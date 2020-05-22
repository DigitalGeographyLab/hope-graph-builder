import sys
sys.path.append('..')
import os
import fiona
from pyproj import CRS
import numpy as np
import pandas as pd
import geopandas as gpd
from common.logger import Logger
import utils as utils
import common.igraph as ig_utils
from common.schema import Edge as E, Node as N
from schema import SamplingGdf as S

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

    # read nodata zone: narrow area between noise surfaces of different municipalities
    nodata_zone = gpd.read_file(nodata_zone_gpkg_layer['gpkg'], layer=nodata_zone_gpkg_layer['layer'])

    # read noise data
    noise_layer_names = [layer for layer in fiona.listlayers(noise_gpkg)]
    noise_layers = { name: gpd.read_file(noise_gpkg, layer=name) for name in noise_layer_names }
    noise_layers = { name: gdf.rename(columns={'db_low':name}) for name, gdf in noise_layers.items() }
    log.info(f'read {len(noise_layers)} noise layers')

    # create sampling points
    gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig])
    gdf = utils.add_sampling_points_to_gdf(gdf, sampling_interval=3)
    point_gdf = utils.explode_sampling_point_gdf(gdf, points_geom_column=S.sampling_points)

    # select only unique sampling points for sampling
    point_gdf = utils.add_unique_geom_id(point_gdf, log)
    uniq_point_gdf = point_gdf.drop_duplicates(S.xy_id, keep='first')
    initial_sampling_count = len(uniq_point_gdf.index)
    log.info(f'created {len(uniq_point_gdf)} unique sampling points ({round(len(point_gdf)/graph.ecount(),2)} per edge)')

    # add boolean column indicating wether sampling point is within potential nodata zone
    uniq_point_gdf = utils.add_inside_nodata_zone_column(uniq_point_gdf, nodata_zone, log)
    # columns: edge_id, sample_len, xy_id, nodata_zone (1 / na)

    if (b_debug == True):
        if os.path.exists(debug_gpkg):
            os.remove(debug_gpkg)
        log.info('exporting edges and sampling points for debugging')
        gdf.drop(columns=[S.sampling_points]).to_file(debug_gpkg, layer='graph_edges', driver='GPKG')
        uniq_point_gdf.to_file(debug_gpkg, layer='sampling_points', driver='GPKG')

    # spatially join noise values by sampling points from a set of noise surface layers
    noise_samples = utils.sjoin_noise_values(uniq_point_gdf, noise_layers, log)
    
    noise_samples[S.no_noise_values] = noise_samples.apply(lambda row: utils.all_noise_values_none(row, noise_layers), axis=1)
    utils.log_none_noise_stats(log, noise_samples)

    # add column indicating wether sampling points is both located in potential nodata_zone and is missing noise values
    noise_samples[S.missing_noises] = noise_samples.apply(lambda row: True if (row[S.nodata_zone] == 1) & (row[S.no_noise_values] == True) else False, axis=1)
    utils.log_missing_noise_stats(noise_samples, log)

    if (b_debug == True):
        noise_samples.to_file(debug_gpkg, layer='sampling_points_noise', driver='GPKG')

    # create extra sampling points for sampling points missing noise values
    missing_noises = noise_samples[noise_samples[S.missing_noises] == True][[S.xy_id, S.geometry]].copy()
    missing_noises[S.extra_sampling_points] = [utils.get_sampling_points_around(point, distance=7, count=20) for point in missing_noises[S.geometry]]
    extra_sampling_points = utils.explode_extra_sampling_point_gdf(missing_noises, S.extra_sampling_points)

    if (b_debug == True):
        extra_sampling_points.to_file(debug_gpkg, layer='extra_sampling_points', driver='GPKG')

    # join noise values to extra sampling points
    extra_sampling_point_noises = utils.sjoin_noise_values(extra_sampling_points, noise_layers, log)
    
    if (b_debug == True):
        extra_sampling_point_noises.to_file(debug_gpkg, layer='extra_sampling_point_noises', driver='GPKG')

    # calculate average noise values per xy_id from extra sampling points
    extra_samples_by_xy_id = extra_sampling_point_noises.groupby(by=S.xy_id)
    row_accumulator = []
    for xy_id, group in extra_samples_by_xy_id:
        samples = group.copy()
        samples = samples.fillna(0)
        extra_sample = {name: samples[name].quantile(.7, interpolation='nearest') for name in noise_layers.keys()}
        extra_sample[S.xy_id] = xy_id
        row_accumulator.append(extra_sample)

    extra_noise_samples = pd.DataFrame(row_accumulator)
    extra_noise_samples = extra_noise_samples.replace(0, np.nan)
    
    # add newly sampled noise values to sampling points missing them
    missing_noises = pd.merge(missing_noises.drop(columns=[S.extra_sampling_points]), extra_noise_samples, on=S.xy_id, how='left')
    if (b_debug == True):
        missing_noises.to_file(debug_gpkg, layer='extra_noise_values', driver='GPKG')

    # add maximum noise values etc. to sampling points
    log.info('finding maximum noise values')
    noise_samples = noise_samples[noise_samples[S.missing_noises] == False].copy()
    noise_samples = utils.aggregate_noise_values(noise_samples)
    missing_noises = utils.aggregate_noise_values(missing_noises, prefer_syke=True)

    # combine sampling point dataframes to one
    sampling_columns = [S.xy_id, S.n_road, S.n_train, S.n_tram, S.n_metro, S.n_max, S.n_max_sources, S.n_max_adj]
    noise_samples = noise_samples[sampling_columns]
    missing_noises = missing_noises[sampling_columns]

    concatenated_samples = pd.concat([noise_samples, missing_noises], ignore_index=True)

    if (concatenated_samples[S.xy_id].nunique() != len(concatenated_samples.index)):
        log.error(f'found invalid number of unique sampling point ids: {len(concatenated_samples.index)} != {concatenated_samples[S.xy_id].nunique()}')
    
    if (initial_sampling_count != len(concatenated_samples.index)):
        log.error(f'found mismatch in sampling point count: {len(concatenated_samples.index)} != {initial_sampling_count}')

    final_samples = pd.merge(point_gdf, concatenated_samples, how='left', on=S.xy_id)
    final_samples_gdf = gpd.GeoDataFrame(final_samples, crs=CRS.from_epsg(3879))

    if (len(final_samples.index) != len(point_gdf.index)):
        log.error(f'mismatch in row counts after merging sampled values to initial sampling points: {len(final_samples.index)} != {len(point_gdf.index)}')

    if (b_debug == True):
        log.info('exporting sampling points to gpkg')
        final_samples_gdf.drop(columns=[S.n_max_sources]).to_file(debug_gpkg, layer='final_noise_samples', driver='GPKG')
    
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
