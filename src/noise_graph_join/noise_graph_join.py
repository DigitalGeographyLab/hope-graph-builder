import sys
sys.path.append('..')
import os
import fiona
import pandas as pd
import geopandas as gpd
from common.logger import Logger
import utils as utils
import common.igraph as ig_utils
from common.schema import Edge as E, Node as N

def noise_graph_join(
    log: Logger, 
    b_debug: bool,
    debug_gpkg: str,
    graph_file: str, 
    noise_gpkg: str, 
    sampling_interval: float, 
    nodata_zone_gpkg_layer: dict
    ):

    graph = ig_utils.read_graphml(graph_file)
    log.info(f'read graph of {graph.ecount()} edges')
    nodata_zone = gpd.read_file(nodata_zone_gpkg_layer['gpkg'], layer=nodata_zone_gpkg_layer['layer'])

    # create sampling points
    gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig])
    gdf = utils.add_sampling_points_to_gdf(gdf, sampling_interval=3)
    point_gdf = utils.explode_sampling_point_gdf(gdf)
    point_gdf = utils.add_unique_geom_id(point_gdf, log)
    uniq_point_gdf = point_gdf.drop_duplicates('xy_id', keep='first')
    log.info(f'created {len(uniq_point_gdf)} unique sampling points ({round(len(point_gdf)/graph.ecount(),2)} per edge)')

    # add boolean column indicating wether sampling point is within potential nodata zone
    uniq_point_gdf = utils.add_inside_nodata_zone_column(uniq_point_gdf, nodata_zone, log)
    # columns: edge_id, sample_len, xy_id, nodata_zone (1 / na)

    if (b_debug == True):
        if os.path.exists(debug_gpkg):
            os.remove(debug_gpkg)
        log.info('exporting edges and sampling points for debugging')
        gdf.drop(columns=['sampling_points']).to_file(debug_gpkg, layer='graph_edges', driver='GPKG')
        uniq_point_gdf.to_file(debug_gpkg, layer='sampling_points', driver='GPKG')

    # spatially join noise values by sampling points from a set of noise surface layers
    noise_layers = [layer for layer in fiona.listlayers(noise_gpkg)]
    point_noises = uniq_point_gdf.copy()
    for layer in noise_layers:
        log.debug(f'joining noise layer [{layer}] to sampling points')
        noise_gdf = gpd.read_file(noise_gpkg, layer=layer)
        noise_gdf = noise_gdf.rename(columns={'db_low':layer})
        point_noises = gpd.sjoin(point_noises, noise_gdf, how='left', op='within').drop(['index_right'], axis=1)
    
    point_noises['no_noise_values'] = point_noises.apply(lambda row: utils.all_noise_values_none(row, noise_layers), axis=1)
    utils.log_none_noise_stats(log, point_noises)

    if (b_debug == True):
        point_noises.to_file(debug_gpkg, layer='sampling_points_noise', driver='GPKG')

    # add column indicating wether sampling points is both located in potential nodata_zone and is missing noise values
    point_noises['missing_noises'] = point_noises.apply(lambda row: True if (row['nodata_zone'] == 1) & (row['no_noise_values'] == True) else False, axis=1)
    utils.log_missing_noise_stats(point_noises, log)

    # create extra sampling points for sampling points missing noise values
    missing_noises = point_noises[point_noises['missing_noises'] == True][['xy_id', 'geometry']].copy()
    missing_noises['sampling_points'] = [utils.get_sampling_points_around(point, distance=12, count=20) for point in missing_noises['geometry']]
    extra_sampling_points = utils.explode_extra_sampling_point_gdf(missing_noises)

    if (b_debug == True):
        extra_sampling_points.to_file(debug_gpkg, layer='extra_sampling_points', driver='GPKG')

    # join noise values to extra sampling points
    extra_sampling_point_noises = extra_sampling_points.copy()
    for layer in noise_layers:
        log.debug(f'joining noise layer [{layer}] to additional sampling points')
        noise_gdf = gpd.read_file(noise_gpkg, layer=layer)
        noise_gdf = noise_gdf.rename(columns={'db_low':layer})
        extra_sampling_point_noises = gpd.sjoin(extra_sampling_point_noises, noise_gdf, how='left', op='within').drop(['index_right'], axis=1)
    
    if (b_debug == True):
        extra_sampling_point_noises.to_file(debug_gpkg, layer='extra_sampling_point_noises', driver='GPKG')

    # calculate average noise values per xy_id from extra sampling points
    extra_samples_by_xy_id = extra_sampling_point_noises.groupby(by='xy_id')
    extra_noise_samples = []
    for name, group in extra_samples_by_xy_id:
        samples = group.copy()
        samples = samples.fillna(0)
        extra_sample = {layer: samples[layer].median() for layer in noise_layers}
        extra_sample['xy_id'] = name
        extra_noise_samples.append(extra_sample)

    extra_noise_samples_df = pd.DataFrame(extra_noise_samples)
    
    # add newly sampled noise values to sampling points missing them
    missing_noises = pd.merge(missing_noises.drop(columns=['sampling_points']), extra_noise_samples_df, on='xy_id', how='left')
    if (b_debug == True):
        missing_noises.to_file(debug_gpkg, layer='extra_noise_values', driver='GPKG')
    
    log.info('all done')

if (__name__ == '__main__'):
    noise_graph_join(
        log = Logger(printing=True, log_file='noise_graph_join.log', level='debug'),
        b_debug = True,
        debug_gpkg = 'debug/noise_join_debug.gpkg',
        graph_file = 'data/test_graph.graphml',
        noise_gpkg = 'data/noise_data_processed.gpkg',
        sampling_interval = 3,
        nodata_zone_gpkg_layer = {'gpkg': 'data/extents.gpkg', 'layer': 'municipal_boundaries'}
    )
