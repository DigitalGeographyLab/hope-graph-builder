import sys
sys.path.append('..')
from shapely.geometry import LineString
from typing import Dict, List, Union
from geopandas import GeoDataFrame
from pandas import DataFrame
import geopandas as gpd
import math
from common.logger import Logger
import common.igraph as ig_utils
from common.igraph import Edge as E
import db
import land_cover_overlay_analysis as lc_analysis


def load_point_gvi_gdf(filepath: str) -> GeoDataFrame:
    g_point_gdf = gpd.read_file(filepath, layer='Helsinki_4326')
    load_gvi = lambda x: round(x / 100, 3)
    g_point_gdf['GVI'] = [load_gvi(gvi_raw) for gvi_raw in g_point_gdf['Gvi_Mean']]
    return g_point_gdf.to_crs(epsg=3879)


sample_ratio = lambda e_count, s_count: round(100 * s_count/e_count, 1)


def get_point_gvi_list_by_way_id(
    log: Logger,
    edge_gdf: GeoDataFrame,
    point_gvi_gdf: GeoDataFrame
) -> Dict[int, List[float]]:
    """Returns a dictionary of lists of point GVI values by edge id. All GVI point values within 30m from edge
    geomtry will be included in the list. 
    """

    edges = edge_gdf[[E.id_way.name, 'geometry']].copy()
    gvi_points = point_gvi_gdf[['geometry', 'GVI']].copy()

    edges['geom_b_30'] = [geom.buffer(30) for geom in edges['geometry']]
    edges = edges.set_geometry('geom_b_30')

    edge_gvi_points = gpd.sjoin(edges, gvi_points, how='inner', op='intersects')
    gvi_points_by_way_id = edge_gvi_points.groupby(E.id_way.name)

    gvi_list_by_way_id = {}
    for way_id, g_points in gvi_points_by_way_id:
        gvi_list_by_way_id[way_id] = list(g_points['GVI'])

    log.info(f'Found GVI point samples for {sample_ratio(len(edges), len(gvi_list_by_way_id))} % edges')

    return gvi_list_by_way_id


def get_mean_edge_point_gvi(
    edge_length: float,
    gvi_list: List[float],
) -> Union[float, None]:
    """Returns mean GVI if there are enough samples in the list with respect to the length of the edge,
    else returns None (i.e. unknown edge GVI). We expect one GVI point per 10 m on streets, and accept 
    no more than half of the points missing (TODO: adjust this logic if needed). 
    """
    required_sample_size = math.floor((edge_length / 10) * 0.5) if edge_length > 20 else 1
    mean = lambda l: round(sum(l) / len(l), 2)
    return mean(gvi_list) if len(gvi_list) >= required_sample_size else None


def get_col_by_col_dict(df: DataFrame, col1: str, col2: str) -> dict:
    col1_values = list(df[col1])
    col2_values = list(df[col2])
    return dict(zip(col1_values, col2_values))


def get_mean_point_gvi_by_way_id(
    log: Logger,
    gvi_list_by_way_id: Dict[int, List[float]], 
    edge_gdf: GeoDataFrame
) -> Dict[int, float]:
    """Calculate mean point GVI for edges. Only edges (way IDs) for which enough GVI point samples
    are found are included in the returned dictionary. 
    """
    edge_length_by_way_id = get_col_by_col_dict(edge_gdf, E.id_way.name, E.length.name)

    mean_point_gvi_by_way_id = { way_id:
        get_mean_edge_point_gvi(edge_length_by_way_id[way_id], gvi_list_by_way_id[way_id])
        for way_id in gvi_list_by_way_id
    }
    na_filtered = { way_id: gvi for way_id, gvi in mean_point_gvi_by_way_id.items() if gvi is not None }
    log.info(f'Got mean point GVI for {sample_ratio(len(edge_gdf), len(na_filtered))} % edges')
    return na_filtered


def combine_gvi_indexes(
    gsv_gvi: Union[float, None],
    low_veg_share: float,
    high_veg_share: float,
    omit_low_veg: bool = False,
    low_veg_gvi_coeff: float = 0.6
) -> float:
    """Returns mean GSV (i.e. point) GVI if present, otherwise returns either high vegetation share
    or combined high and low vegetation shares as "GVI". In the combined GVI, the effect of low
    vegetation share is reduced by the given coefficient low_veg_gvi_coeff (float). 
    """
    if gsv_gvi:
        return round(gsv_gvi, 2)
    elif omit_low_veg:
        return round(high_veg_share, 2)
    else:
        comb_lc_gvi = high_veg_share + low_veg_gvi_coeff * low_veg_share
        return round(comb_lc_gvi, 2)


if __name__ == '__main__':
    log = Logger(printing=True, log_file=r'green_view_join_v1.log', level='debug')

    subset = True

    graph_file_in = r'graph_in/kumpula.graphml' if subset else r'graph_in/hma.graphml'
    graph_file_out = r'graph_out/kumpula.graphml' if subset else r'graph_out/hma.graphml'
    edge_table_db_name = 'edge_buffers_subset' if subset else 'edge_buffers'

    execute_sql = db.get_sql_executor(log)
    db_tables = db.get_db_table_names(execute_sql)

    # load GVI points from GPKG
    point_gvi_gdf = load_point_gvi_gdf(r'data/greenery_points.gpkg')
    
    # load street network graph from GraphML
    graph = ig_utils.read_graphml(graph_file_in)
    log.info(f'Read graph of {graph.ecount()} edges')

    # load edge_gdf
    edge_gdf: GeoDataFrame = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length, E.id_way])
    edge_gdf = edge_gdf.drop_duplicates(E.id_way.name, keep = 'first')
    # drop edges without geometry
    edge_gdf = edge_gdf[edge_gdf['geometry'].apply(lambda geom: isinstance(geom, LineString))]
    log.info(f'Subset edge_gdf to {len(edge_gdf)} unique geometries')

    # export edges to db if not there yet for land cover overlay analysis
    if edge_table_db_name not in db_tables:
        # add simplified buffers to edge_gdf
        edges_2_db = edge_gdf.copy()
        log.info(f'Calculating 30m buffers from edge geometries')
        edges_2_db['b30'] = [geom.buffer(30, resolution=3) for geom in edges_2_db['geometry']]
        edges_2_db = edges_2_db.rename(columns={'geometry': 'line_geom', 'b30': 'geometry'})
        edges_2_db = edges_2_db.set_geometry('geometry')

        log.info('Writing edges to PostGIS')
        write_to_postgis = db.get_db_writer(log)
        write_to_postgis(edges_2_db[[E.id_way.name, 'geometry']], edge_table_db_name)

        log.info('Wrote graph edges to db, run land_cover_overlay_analysis.py next')
        exit()
    
    else:
        log.info(f'Edges were already exported to db table: {edge_table_db_name}')
    
    # get mean point GVI per edge
    point_gvi_list_by_way_id = get_point_gvi_list_by_way_id(log, edge_gdf, point_gvi_gdf)
    mean_point_gvi_by_way_id = get_mean_point_gvi_by_way_id(log, point_gvi_list_by_way_id, edge_gdf)

    # fetch low and high vegetation shares from db per edge buffer (way ID)
    low_veg_share_by_way_id = lc_analysis.get_low_veg_share_by_way_id()
    high_veg_share_by_way_id = lc_analysis.get_high_veg_share_by_way_id()

    # set default GVI attributes to graph
    graph.es[E.gvi_gsv.value] = None
    graph.es[E.gvi_low_veg_share.value] = None
    graph.es[E.gvi_high_veg_share.value] = None
    graph.es[E.gvi_comb_gsv_veg.value] = None
    graph.es[E.gvi_comb_gsv_high_veg.value] = None

    # set calculated GVI attribute values to graph
    for e in graph.es:
        attrs = e.attributes()
        way_id = attrs[E.id_way.value]

        # let's only update GVI values for edges with geometry
        if isinstance(attrs[E.geometry.value], LineString):
            gsv_gvi = mean_point_gvi_by_way_id.get(way_id, None)
            low_veg_share = low_veg_share_by_way_id.get(way_id, 0.0)
            high_veg_share = high_veg_share_by_way_id.get(way_id, 0.0)

            graph.es[e.index].update_attributes({
                # if GSV GVI is not found, there were no pictures on the edge
                E.gvi_gsv.value: gsv_gvi,
                # if land cover GVI (vegetation share) is not found, there is no vegetation
                E.gvi_low_veg_share.value: low_veg_share,
                E.gvi_high_veg_share.value: high_veg_share,
                E.gvi_comb_gsv_veg.value: combine_gvi_indexes(gsv_gvi, low_veg_share, high_veg_share),
                E.gvi_comb_gsv_high_veg.value: combine_gvi_indexes(
                    gsv_gvi, low_veg_share, high_veg_share, omit_low_veg=True
                )
            })

    ig_utils.export_to_graphml(graph, graph_file_out)

    log.info(f'Exported graph to file {graph_file_out}')
