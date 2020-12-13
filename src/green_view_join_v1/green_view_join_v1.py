import sys
sys.path.append('..')
from shapely.geometry import LineString
from typing import Dict, List, Union
from geopandas import GeoDataFrame
import geopandas as gpd
import math
from common.logger import Logger
import common.igraph as ig_utils
from common.igraph import Edge as E
from db import get_db_writer


def load_point_gvi_gdf(filepath: str) -> GeoDataFrame:
    g_point_gdf = gpd.read_file(filepath, layer='Helsinki_4326')
    load_gvi = lambda x: round(x / 100, 3)
    g_point_gdf['GVI'] = [load_gvi(gvi_raw) for gvi_raw in g_point_gdf['Gvi_Mean']]
    return g_point_gdf.to_crs(epsg=3879)


sample_ratio = lambda e_count, s_count: round(100 * s_count/e_count, 1)


def get_point_gvi_list_by_edge_id(
    log: Logger,
    edge_gdf: GeoDataFrame,
    point_gvi_gdf: GeoDataFrame
) -> Dict[int, List[float]]:
    """Returns a dictionary of lists of point GVI values by edge id. All GVI point values within 30m from edge
    geomtry will be included in the list. 
    """

    edges = edge_gdf[[E.id_ig.name, 'geometry']].copy()
    gvi_points = point_gvi_gdf[['geometry', 'GVI']].copy()

    edges['geom_b_30'] = [geom.buffer(30) for geom in edges['geometry']]
    edges = edges.set_geometry('geom_b_30')

    edge_g_points = gpd.sjoin(edges, gvi_points, how='inner', op='intersects')
    g_points_by_edge_id = edge_g_points.groupby(E.id_ig.name)

    gvi_list_by_edge_id = {}
    for edge_id, g_points in g_points_by_edge_id:
        gvi_list_by_edge_id[edge_id] = list(g_points['GVI'])

    log.info(f'Found GVI point samples for {sample_ratio(len(edges), len(gvi_list_by_edge_id))} % edges')

    return gvi_list_by_edge_id


def get_mean_edge_point_gvi(
    gvi_list: List[float], 
    e_length: float
) -> Union[float, None]:
    """Returns mean GVI if there are enough samples in the list with respect to the length of the edge,
    else returns None (i.e. unknown edge GVI). We expect one GVI point per 10 m on streets, and accept 
    no more than half of the points missing (TODO: adjust this logic if needed). 
    """
    required_sample_size = math.floor((e_length / 10) * 0.5) if e_length > 20 else 1
    mean = lambda l: round(sum(l) / len(l), 2)
    return mean(gvi_list) if len(gvi_list) >= required_sample_size else None


def add_mean_point_gvi(
    log: Logger,
    gvi_list_by_edge_id: Dict[int, List[float]], 
    edge_gdf: GeoDataFrame
) -> GeoDataFrame:
    """Adds new column to edge_gdf with name "mean_p_GVI" containing
    mean GVI values from point GVI data.
    """

    edge_gdf['mean_p_GVI'] = edge_gdf.apply(
        lambda row: get_mean_edge_point_gvi(
            gvi_list_by_edge_id.get(row[E.id_ig.name], []),
            row[E.length.name]
        ), axis=1
    )

    count_joined_gvi = edge_gdf['mean_p_GVI'].count()
    log.info(f'Joined GVI mean values to {sample_ratio(len(edge_gdf), count_joined_gvi)} % edges')

    return edge_gdf


if __name__ == '__main__':
    log = Logger(printing=True, log_file=r'green_view_join_v1.log', level='debug')

    subset = True

    graph_file_in = r'graph_in/kumpula.graphml' if subset else r'graph_in/hma.graphml'
    edge_table_db_name = 'edge_buffers_subset' if subset else 'edge_buffers'

    # load GVI points from GPKG
    point_gvi_gdf_file = r'data/greenery_points.gpkg'
    point_gvi_gdf = load_point_gvi_gdf(point_gvi_gdf_file)
    
    # load street network graph from GraphML
    graph = ig_utils.read_graphml(graph_file_in)
    log.info(f'Read graph of {graph.ecount()} edges')

    # load edge_gdf
    edge_gdf: GeoDataFrame = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length, E.id_way])
    edge_gdf = edge_gdf.drop_duplicates(E.id_way.name, keep = 'first')
    # drop edges without geometry
    edge_gdf = edge_gdf[edge_gdf['geometry'].apply(lambda geom: isinstance(geom, LineString))]
    log.info(f'Subset edge_gdf to {len(edge_gdf)} unique geometries')

    # join mean point GVI to edge_gdf
    gvi_list_by_edge_id = get_point_gvi_list_by_edge_id(log, edge_gdf, point_gvi_gdf)
    edge_gdf = add_mean_point_gvi(log, gvi_list_by_edge_id, edge_gdf)
    
    # add simplified buffers to edge_gdf
    log.info(f'Calculating 30m buffers from edge geometries')
    edge_gdf['b30'] = [geom.buffer(30, resolution=3) for geom in edge_gdf['geometry']]
    edge_gdf = edge_gdf.rename(columns={'geometry': 'line_geom', 'b30': 'geometry'})
    edge_gdf = edge_gdf.set_geometry('geometry')

    log.info('Writing edges to PostGIS')
    write_to_postgis = get_db_writer(log)
    write_to_postgis(edge_gdf[[E.id_ig.name, 'geometry']], edge_table_db_name)

    # TODO overlay analysis with vegetation layers
