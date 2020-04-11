import sys
sys.path.append('..')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from shapely.geometry import Point, LineString
import numpy as np
import pandas as pd
import geopandas as gpd
import igraph as ig
import shapely.wkt
from fiona.crs import from_epsg
import utils.igraph as ig_utils
from utils.logger import Logger

export_to_gpkg: bool = False
otp_graph_gpkg = 'otp_graph_data/otp_graph_features.gpkg'
graph_debug_gpkg = 'otp_graph_data/otp_igraph_debug.gpkg'
log = Logger(printing=True, log_file='otp2igraph_import.log', level='info')

# 1) read OTP graph data from CSV files

# edges
e = pd.read_csv('otp_graph_data/edges.csv', sep=';')
e = e.rename(columns={'id': 'id_otp'})
log.info(f'read {len(e.index)} edges')
log.debug(f'edge column types: {e.dtypes}')
log.debug(f'edges head: {e.head()}')
log.info('reading edges to gdf')
e['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e['geometry']]
e['geom_wgs'] = e['geometry']
e = gpd.GeoDataFrame(e, geometry='geometry', crs=from_epsg(4326))
log.info('reprojecting edges to etrs')
e = e.to_crs(epsg=3879)
log.debug(f'edges head: {e.head()}')

# nodes
n = pd.read_csv('otp_graph_data/nodes.csv', sep=';')
n = n.rename(columns={'id': 'id_otp'})
log.info(f'read {len(n.index)} nodes')
log.debug(f'node column types: {n.dtypes}')
log.debug(f'nodes head: {n.head()}')
log.info('reading nodes to gdf')
n['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else Point() for geom in n['geometry']]
e['geom_wgs'] = e['geometry']
n = gpd.GeoDataFrame(n, geometry='geometry', crs=from_epsg(4326))
log.info('reprojecting nodes to etrs')
n = n.to_crs(epsg=3879)
log.debug(f'nodes head: {n.head()}')

if (export_to_gpkg == True):
    log.info('writing graph data to gpkg')
    e.to_file(otp_graph_gpkg, layer='edges', driver='GPKG')
    log.info(f'exported edges to {otp_graph_gpkg} (layer=edges)')
    n.to_file(otp_graph_gpkg, layer='nodes', driver='GPKG')
    log.info(f'exported nodes to {otp_graph_gpkg} (layer=nodes)')

def filter_df_by_query(df: pd.DataFrame, query: str, name: str = 'rows'):
    count_before = len(df.index)
    df_filt = df.query(query).copy()
    filt_ratio = round((count_before-len(df_filt.index)) / count_before, 3)
    log.info(f'filtered out {count_before-len(df_filt.index)} {name} ({filt_ratio * 100} %) by {query}')
    return df_filt

# 2) filter out edges that are unsuitable for both walking and cycling
e_filt = filter_df_by_query(e, 'allows_walking == True or allows_biking == True', name='edges')
e_filt = filter_df_by_query(e_filt, 'is_no_thru_traffic == False', name='edges')

# 3) create a dictionaries for converting otp ids to ig ids and vice versa
log.debug('create maps for converting otp ids to ig ids')
n['id_ig'] = np.arange(len(n.index))
ids_otp_ig = {}
ids_ig_otp = {}
for node in n.itertuples():
    ids_otp_ig[getattr(node, 'id_otp')] = getattr(node, 'id_ig')
    ids_ig_otp[getattr(node, 'id_ig')] = getattr(node, 'id_otp')
    
# 4) add nodes to graph
log.info('adding nodes to graph')
G = ig.Graph(directed=True)
G.add_vertices(len(n.index))
G.vs['id_otp'] = list(n['id_otp'])
G.vs['id_ig'] = list(n['id_ig'])
G.vs['geometry'] = list(n['geometry'])

# 5) add edges to graph
log.info('adding edges to graph')

def get_ig_uv(edge):
    return (ids_otp_ig[edge['nodeOrigId']], ids_otp_ig[edge['nodeDestId']])

e_filt['uv_ig'] = e_filt.apply(lambda row: get_ig_uv(row), axis=1)
e_filt['id_ig'] = np.arange(len(e_filt.index))
G.add_edges(list(e_filt['uv_ig']))
G.es['id_otp'] = list(e_filt['id_otp'])
G.es['id_ig'] = list(e_filt['id_ig'])
G.es['uv_ig'] = list(e_filt['uv_ig'])
G.es['geometry'] = list(e_filt['geometry'])
# TODO add rest of the edge attributes

# 6) find and inspect subgraphs by decomposing the graph
sub_graphs = G.decompose(mode='STRONG')
log.info(f'found {len(sub_graphs)} subgraphs')

graph_sizes = [graph.ecount() for graph in sub_graphs]
log.info(f'subgraphs with more than 10 edges: {len([s for s in graph_sizes if s > 10])}')
log.info(f'subgraphs with more than 50 edges: {len([s for s in graph_sizes if s > 50])}')
log.info(f'subgraphs with more than 100 edges: {len([s for s in graph_sizes if s > 100])}')
log.info(f'subgraphs with more than 500 edges: {len([s for s in graph_sizes if s > 500])}')
log.info(f'subgraphs with more than 10000 edges: {len([s for s in graph_sizes if s > 10000])}')

small_graphs = [graph for graph in sub_graphs if graph.ecount() <= 10]
medium_graphs = [graph for graph in sub_graphs if (graph.ecount() > 10 and graph.ecount() <= 500)]
big_graphs = [graph for graph in sub_graphs if graph.ecount() > 500]

small_graph_edges = []
for graph_id, graph in enumerate(small_graphs):
    edges = ig_utils.get_edge_dicts(graph, attrs=['id_otp', 'id_ig', 'geometry'])
    for edge in edges:
        edge['graph_id'] = graph_id
    small_graph_edges.extend(edges)

medium_graph_edges = []
for graph_id, graph in enumerate(medium_graphs):
    edges = ig_utils.get_edge_dicts(graph, attrs=['id_otp', 'id_ig', 'geometry'])
    for edge in edges:
        edge['graph_id'] = graph_id
    medium_graph_edges.extend(edges)

big_graph_edges = []
for graph_id, graph in enumerate(big_graphs):
    edges = ig_utils.get_edge_dicts(graph, attrs=['id_otp', 'id_ig', 'geometry'])
    for edge in edges:
        edge['graph_id'] = graph_id
    big_graph_edges.extend(edges)

if (export_to_gpkg == True):
    log.info('exporting subgraphs to gpkg')
    # graphs with <= 10 edges
    small_graph_edges_gdf = gpd.GeoDataFrame(small_graph_edges, crs=from_epsg(4326))
    log.info(f'{small_graph_edges_gdf.head()}')
    small_graph_edges_gdf.to_file(graph_debug_gpkg, layer='small_graph_edges', driver='GPKG')
    # graphs with  10–500 edges
    medium_graph_edges_gdf = gpd.GeoDataFrame(medium_graph_edges, crs=from_epsg(4326))
    log.info(f'{medium_graph_edges_gdf.head()}')
    medium_graph_edges_gdf.to_file(graph_debug_gpkg, layer='medium_graph_edges', driver='GPKG')
    # graphs with > 500 edges
    big_graph_edges_gdf = gpd.GeoDataFrame(big_graph_edges, crs=from_epsg(4326))
    log.info(f'{big_graph_edges_gdf.head()}')
    big_graph_edges_gdf.to_file(graph_debug_gpkg, layer='big_graph_edges', driver='GPKG')
    log.info(f'graphs exported')

# 7) collect IDs of the edges that need to be removed
rm_edge_ids = [edge['id_ig'] for edge in small_graph_edges]

# TODO select a subset of the graph by HMA

# TODO remove isolated nodes from the graph
# rm_node_ids = list(G.vs.select(_degree_eq=0))
