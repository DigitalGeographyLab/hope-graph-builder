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
    """Exploads new rows from dataframe by lists of sampling points in column 'sampling_points'.
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

def print_none_noise_stats(log: Logger, gdf: gpd.GeoDataFrame) -> None:
    missing_count = len(gdf[gdf['missing_noise'] == True])
    missing_ratio = round(100 * missing_count/len(gdf.index), 2)
    log.info(f'found {missing_count} ({missing_ratio} %) sampling points with missing values')

def add_inside_nodata_zone_column(gdf, nodata_zone, log: Logger=None):
    joined = gpd.sjoin(gdf, nodata_zone, how='left', op='within').drop(['index_right'], axis=1)
    if (log != None):
        nodata_zone_count = len(joined[joined['nodata_zone'] == 1])
        nodata_zone_share = round(100 * nodata_zone_count/len(gdf.index), 2)
        log.info(f'found {nodata_zone_count} ({nodata_zone_share} %) sampling points inside potential nodata zone')
    return joined

def get_sampling_points_missing_noise_data(gdf, log: Logger=None):
    missing_noise_gdf = gdf[(gdf['nodata_zone'] == 1) & (gdf['missing_noise'] == True)].copy()
    if (log != None):
        missing_count = len(missing_noise_gdf)
        missing_share = round(100 * missing_count/len(gdf.index), 2)
        log.info(f'found {missing_count} ({missing_share} %) sampling points for which noise values need to be interpolated')
    return missing_noise_gdf
