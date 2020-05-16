from shapely.geometry import LineString, Point, GeometryCollection
from typing import List, Set, Dict, Tuple
from pyproj import CRS
import geopandas as gpd

def get_point_sampling_distances(sample_count: int):
    """Calculates set of distances for sample points as relative shares. 
    """
    sampling_interval = 1/sample_count
    sp_indexes = range(0, sample_count)
    sample_distances = [sampling_interval/2 + sp_index * sampling_interval for sp_index in sp_indexes]
    return sample_distances

def get_sampling_points(geom: LineString, sampling_interval: int):
    """Finds and returns sample points as Point objects for a LineString object (geom). Sampling interval (m) is 
    given as argument sampling_interval.  
    """
    sample_count = round(geom.length / sampling_interval)
    sample_count = sample_count if sample_count != 0 else 1
    sample_distances = get_point_sampling_distances(sample_count)
    sampling_points: List[Point] = [geom.interpolate(distance, normalized=True) for distance in sample_distances]
    return sampling_points

def add_sampling_points_to_gdf(gdf, sampling_interval: int):
    """Adds new column 'sampling_points' with sampling points by specified interval (m) (sampling_interval).
    """
    gdf['sampling_points'] = [get_sampling_points(geom, sampling_interval) if isinstance(geom, LineString) else None for geom in gdf['geometry'].values]
    return gdf

def explode_sampling_point_gdf(gdf):
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
