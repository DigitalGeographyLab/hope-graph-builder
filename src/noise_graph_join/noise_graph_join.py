import sys
sys.path.append('..')
import os
import fiona
import geopandas as gpd
from common.logger import Logger
import utils as utils
import common.igraph as ig_utils
from common.schema import Edge as E, Node as N

def noise_graph_join(
    log: Logger, 
    b_debug: bool, 
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

    # add boolean column indicating wether sampling points is within potential nodata zone
    uniq_point_gdf = utils.add_inside_nodata_zone_column(uniq_point_gdf, nodata_zone, log)
    # columns: edge_id, sample_len, xy_id, nodata_zone (1 / na)

    if (b_debug == True):
        if os.path.exists('debug/noise_join_debug.gpkg'):
            os.remove('debug/noise_join_debug.gpkg')
        log.info('exporting edges and sampling points for debugging')
        gdf.drop(columns=['sampling_points']).to_file('debug/noise_join_debug.gpkg', layer='graph_edges', driver='GPKG')
        uniq_point_gdf.to_file('debug/noise_join_debug.gpkg', layer='sampling_points', driver='GPKG')

    # spatially join noise values by sampling points from a set of noise surface layers
    noise_layers = [layer for layer in fiona.listlayers(noise_gpkg)]
    point_noises = uniq_point_gdf.copy()
    for layer in noise_layers:
        log.debug(f'joining noise layer: {layer}')
        noise_gdf = gpd.read_file(noise_gpkg, layer=layer)
        noise_gdf = noise_gdf.rename(columns={'db_low':layer})
        point_noises = gpd.sjoin(point_noises, noise_gdf, how='left', op='within').drop(['index_right'], axis=1)
    
    point_noises['missing_noise'] = point_noises.apply(lambda row: utils.all_noise_values_none(row, noise_layers), axis=1)
    utils.print_none_noise_stats(log, point_noises)

    if (b_debug == True):
        point_noises.to_file('debug/noise_join_debug.gpkg', layer='sampling_points_noise', driver='GPKG')

    missing_noises = utils.get_sampling_points_missing_noise_data(point_noises, log)

    log.info('all done')

if (__name__ == '__main__'):
    noise_graph_join(
        log = Logger(printing=True, log_file='noise_graph_join.log', level='debug'),
        b_debug = True,
        graph_file = 'data/test_graph.graphml',
        noise_gpkg = 'data/noise_data_processed.gpkg',
        sampling_interval = 3,
        nodata_zone_gpkg_layer = {'gpkg': 'data/extents.gpkg', 'layer': 'municipal_boundaries'}
    )
