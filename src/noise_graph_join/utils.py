import sys
sys.path.append('..')
import numpy as np
from shapely.geometry import LineString, Point, GeometryCollection
from typing import List, Set, Dict, Tuple
from pyproj import CRS
import geopandas as gpd
from common.logger import Logger

def get_point_sampling_distances(sample_count: int) -> List[float]:
    """Calculates set of distances for sample points as relative shares. 
    """
    sampling_interval = 1/sample_count
    sp_indexes = range(0, sample_count)
    sample_distances = [sampling_interval/2 + sp_index * sampling_interval for sp_index in sp_indexes]
    return sample_distances

def get_sampling_points(geom: LineString, sampling_interval: int) -> List[Point]:
    """Finds and returns sample points as Point objects for a LineString object (geom). Sampling interval (m) is 
    given as argument sampling_interval.  
    """
    sample_count = round(geom.length / sampling_interval)
    sample_count = sample_count if sample_count != 0 else 1
    sample_distances = get_point_sampling_distances(sample_count)
    return [geom.interpolate(distance, normalized=True) for distance in sample_distances]

def add_sampling_points_to_gdf(gdf, sampling_interval: int) -> gpd.GeoDataFrame:
    """Adds new column 'sampling_points' with sampling points by specified interval (m) (sampling_interval).
    """
    gdf['sampling_points'] = [get_sampling_points(geom, sampling_interval) if isinstance(geom, LineString) else None for geom in gdf['geometry'].values]
    return gdf

def explode_sampling_point_gdf(gdf) -> gpd.GeoDataFrame:
    """Exploads new rows from dataframe by lists of sampling points in column 'sampling_points'. Also adds new column sample_len that
    it is calculated simply by dividing the length of the edge by the number of sampling points for it.
    """
    row_accumulator = []
    def explode_by_sampling_points(row):
        if (row['sampling_points'] != None):
            point_count = len(row['sampling_points'])
            sampling_interval = round(row['geometry'].length/point_count, 10)
            for point_geom in row['sampling_points']:
                new_row = {}
                new_row['edge_id'] = row.name
                new_row['sample_len'] = sampling_interval
                new_row['geometry'] = point_geom
                row_accumulator.append(new_row)
    
    gdf.apply(explode_by_sampling_points, axis=1)
    point_gdf = gpd.GeoDataFrame(row_accumulator, crs=CRS.from_epsg(3879))
    return point_gdf

def add_unique_geom_id(point_gdf: gpd.GeoDataFrame, log: Logger=None) -> gpd.GeoDataFrame:
    point_gdf['xy_id'] = [f'{str(round(geom.x, 1))}_{str(round(geom.y, 1))}' for geom in point_gdf['geometry']]
    unique_count = point_gdf['xy_id'].nunique()
    unique_share = round(100 * unique_count/len(point_gdf.index), 2)
    if (log != None):
        log.info(f'found {unique_count} unique sampling points ({unique_share} %)')
    return point_gdf

def all_noise_values_none(row, noise_layers: list) -> bool:
    return all([np.isnan(row[layer]) for layer in noise_layers])

def log_none_noise_stats(log: Logger, gdf: gpd.GeoDataFrame) -> None:
    missing_count = len(gdf[gdf['no_noise_values'] == True])
    missing_ratio = round(100 * missing_count/len(gdf.index), 2)
    log.info(f'found {missing_count} ({missing_ratio} %) sampling points without noise values')

def add_inside_nodata_zone_column(gdf, nodata_zone: gpd.GeoDataFrame, log: Logger=None) -> gpd.GeoDataFrame:
    """Adds boolean column (nodata_zone) indicating whether the points in the gdf are within the given nodata_zone polygon.

    Args:
        gdf: A GeoDataFrame object of sampling points. 
        nodata_zone: A GeoDataFrame object with one feature in it. It must have one attribute (nodata_zone) with value 1. 
    """
    joined = gpd.sjoin(gdf, nodata_zone, how='left', op='within').drop(['index_right'], axis=1)
    if (log != None):
        nodata_zone_count = len(joined[joined['nodata_zone'] == 1])
        nodata_zone_share = round(100 * nodata_zone_count/len(gdf.index), 2)
        log.info(f'found {nodata_zone_count} ({nodata_zone_share} %) sampling points inside potential nodata zone')
    return joined

def log_missing_noise_stats(gdf, log: Logger) -> None:
    """Returns sampling points located at possible nodata_zone and missing noise data. For these sampling points,
    noise values need to be interpolated later. Selection is done by columns nodata_zone (=1) and no_noise_values (=True).
    """
    missing_noises_count = len(gdf[gdf['missing_noises'] == True])
    if (log != None):
        missing_share = round(100 * missing_noises_count/len(gdf.index), 2)
        log.info(f'found {missing_noises_count} ({missing_share} %) sampling points for which noise values need to be interpolated')

def get_sampling_points_around(point: Point, distance: float, count: int=20) -> List[Point]:
    """Returns a set of sampling points at specified distance around a given point.
    """
    buffer = point.buffer(distance)
    boundary = buffer.boundary
    sampling_distances = get_point_sampling_distances(count)
    sampling_points = [boundary.interpolate(dist, normalized=True) for dist in sampling_distances]
    return sampling_points

def explode_extra_sampling_point_gdf(gdf):
    """Explodes dataframe of sampling points by column containing alternative sampling points for each sampling points. Here this
    is used to sample values for those sampling points that are located in small nodata zones. 
    """
    row_accumulator = []
    def explode_sampling_point_rows(row):
        for point in row['sampling_points']:
            new_row = row.to_dict()
            del new_row['sampling_points']
            new_row['geometry'] = point
            row_accumulator.append(new_row)

    gdf.apply(explode_sampling_point_rows, axis=1)
    return gpd.GeoDataFrame(row_accumulator, crs=CRS.from_epsg(3879))

def remove_duplicate_samples(sample_gdf, sample_id: str, noise_layers: dict) -> gpd.GeoDataFrame:
    distinct_samples = []
    samples_by_id = sample_gdf.groupby(by=sample_id)
    for sample_id, samples in samples_by_id:
        # get first row as dictionary
        distinct_sample = samples[:1].to_dict('records')[0]
        if (len(samples) == 1):
            distinct_samples.append(distinct_sample)
        else:
            # use maximum noise values from overlapping (invalid) noise surfaces
            noise_values = { name: samples[name].max() for name in noise_layers.keys() }
            distinct_sample.update(noise_values)
            distinct_samples.append(distinct_sample)
    return gpd.GeoDataFrame(distinct_samples, crs=CRS.from_epsg(3879))

def sjoin_noise_values(gdf, noise_layers: dict, log: Logger=None) -> gpd.GeoDataFrame:
    sample_gdf = gdf.copy()
    sample_gdf['sample_id'] = sample_gdf.index
    for name, noise_gdf in noise_layers.items():
        log.debug(f'joining noise layer [{name}] to sampling points')
        sample_gdf = gpd.sjoin(sample_gdf, noise_gdf, how='left', op='within').drop(['index_right'], axis=1)

    if (len(sample_gdf.index) > len(gdf.index)):
        log.warning(f'joined multiple noise values for one or more sampling points ({len(sample_gdf.index)} != {len(gdf.index)})')

    distinct_samples = remove_duplicate_samples(sample_gdf, 'sample_id', noise_layers)

    if (len(distinct_samples.index) == len(gdf.index)):
        log.info('successfully removed duplicate samples')
    else:
        log.error('error in removing duplicate samples')

    if (list(sample_gdf.columns).sort() != list(distinct_samples.columns).sort()):
        log.error('schema of the dataframe was altered during removing duplicate samples')

    return distinct_samples.drop(columns=['sample_id'])
