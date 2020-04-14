from typing import List, Set, Dict, Tuple
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
import common.igraph as ig_utils
import common.geometry as geom_utils
from common.logger import Logger

log = Logger(printing=True, log_file='otp2igraph_import.log', level='info')
hma_poly = geom_utils.project_geom(gpd.read_file('HMA.geojson')['geometry'][0])
export_otp_data_to_gpkg: bool = True
export_decomposed_igraphs_to_gpkg: bool = True
export_final_graph_to_gpkg: bool = True
debug_otp_graph_gpkg = 'debug/otp_graph_features.gpkg'
debug_igraph_gpkg = 'debug/otp2igraph_features.gpkg'

# 1) read nodes nodes from CSV
n = pd.read_csv('otp_graph_data/nodes.csv', sep=';')
n = n.rename(columns={'id': 'id_otp'})
log.info(f'read {len(n.index)} nodes')
log.debug(f'node column types: {n.dtypes}')
log.debug(f'nodes head: {n.head()}')
log.info('creating node gdf')
n['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else Point() for geom in n['geometry']]
n['geom_wgs'] = n['geometry']
n = gpd.GeoDataFrame(n, geometry='geometry', crs=from_epsg(4326))
log.info('reprojecting nodes to etrs')
n = n.to_crs(epsg=3879)
log.debug(f'nodes head: {n.head()}')

# 2) read edges from CSV
e = pd.read_csv('otp_graph_data/edges.csv', sep=';')
e = e.rename(columns={'id': 'id_otp'})
log.info(f'read {len(e.index)} edges')
log.debug(f'edge column types: {e.dtypes}')
log.debug(f'edges head: {e.head()}')
log.info('creating edge gdf')
e['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e['geometry']]
e['geom_wgs'] = e['geometry']
e = gpd.GeoDataFrame(e, geometry='geometry', crs=from_epsg(4326))
log.info('reprojecting edges to etrs')
e = e.to_crs(epsg=3879)
log.debug(f'edges head: {e.head()}')

# 3) export graph data go gpkg
if (export_otp_data_to_gpkg == True):
    log.info('writing otp graph data to gpkg')
    e.drop(columns=['geom_wgs']).to_file(debug_otp_graph_gpkg, layer='edges', driver='GPKG')
    log.info(f'exported edges to {debug_otp_graph_gpkg} (layer=edges)')
    n.drop(columns=['geom_wgs']).to_file(debug_otp_graph_gpkg, layer='nodes', driver='GPKG')
    log.info(f'exported nodes to {debug_otp_graph_gpkg} (layer=nodes)')

# 4) filter out edges that are unsuitable for both walking and cycling
def filter_df_by_query(df: pd.DataFrame, query: str, name: str = 'rows'):
    count_before = len(df.index)
    df_filt = df.query(query).copy()
    filt_ratio = round((count_before-len(df_filt.index)) / count_before, 3)
    log.info(f'filtered out {count_before-len(df_filt.index)} {name} ({filt_ratio * 100} %) by {query}')
    return df_filt

e_filt = filter_df_by_query(e, 'allows_walking == True or allows_biking == True', name='edges')
e_filt = filter_df_by_query(e_filt, 'is_no_thru_traffic == False', name='edges')

# 5) create a dictionaries for converting otp ids to ig ids and vice versa
log.debug('create maps for converting otp ids to ig ids')
n['id_ig'] = np.arange(len(n.index))
ids_otp_ig = {}
ids_ig_otp = {}
for node in n.itertuples():
    ids_otp_ig[getattr(node, 'id_otp')] = getattr(node, 'id_ig')
    ids_ig_otp[getattr(node, 'id_ig')] = getattr(node, 'id_otp')
    
# 6) add nodes to graph
log.info('adding nodes to graph')
G = ig.Graph(directed=True)
G.add_vertices(len(n.index))
G.vs['id_otp'] = list(n['id_otp'])
G.vs['geometry'] = list(n['geometry'])

# 7) add edges to graph
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

# 8) delete edges outside Helsinki Metropolitan Area (HMA)
hma_buffered = hma_poly.buffer(100)

def intersects_hma(geom: LineString):
    if (geom.is_empty == True): return True
    return True if geom.intersects(hma_buffered) else False

e_gdf = ig_utils.get_edge_gdf(G)
log.info('finding edges that intersect with HMA')
e_gdf['in_hma'] = [intersects_hma(line) for line in e_gdf['geometry']]
e_gdf_del = e_gdf.query('in_hma == False').copy()
out_ratio = round(100 * len(e_gdf_del.index)/len(e_gdf.index), 1)
log.info(f'found {len(e_gdf_del.index)} ({out_ratio} %) edges outside HMA')

log.info('deleting edges')
before_count = G.ecount()
G.delete_edges(e_gdf_del.index.tolist())
after_count = G.ecount()
log.info(f'deleted {before_count-after_count} edges')

# check if id_ig:s need to be updated to edge attributes
mismatch_count = len([edge.index for edge in G.es if edge.attributes()['id_ig'] != edge.index])
log.info(f'invalid edge ids: {mismatch_count}')
# reassign igraph indexes to edge and node attributes
G.es['id_ig'] = [e.index for e in G.es]
G.vs['id_ig'] = [v.index for v in G.vs]
# check if id_ig:s need to be updated to edge attributes
mismatch_count = len([edge.index for edge in G.es if edge.attributes()['id_ig'] != edge.index])
log.info(f'invalid edge ids: {mismatch_count} (after re-indexing)')

# 9) find and inspect subgraphs by decomposing the graph
sub_graphs = G.decompose(mode='STRONG')
log.info(f'found {len(sub_graphs)} subgraphs')

graph_sizes = [graph.ecount() for graph in sub_graphs]
log.info(f'subgraphs with more than 10 edges: {len([s for s in graph_sizes if s > 10])}')
log.info(f'subgraphs with more than 50 edges: {len([s for s in graph_sizes if s > 50])}')
log.info(f'subgraphs with more than 100 edges: {len([s for s in graph_sizes if s > 100])}')
log.info(f'subgraphs with more than 500 edges: {len([s for s in graph_sizes if s > 500])}')
log.info(f'subgraphs with more than 10000 edges: {len([s for s in graph_sizes if s > 10000])}')

small_graphs = [graph for graph in sub_graphs if graph.ecount() <= 15]
medium_graphs = [graph for graph in sub_graphs if (graph.ecount() > 15 and graph.ecount() <= 500)]
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

if (export_decomposed_igraphs_to_gpkg == True):
    log.info('exporting subgraphs to gpkg')
    # graphs with <= 15 edges
    small_graph_edges_gdf = gpd.GeoDataFrame(small_graph_edges, crs=from_epsg(3879))
    small_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='small_graph_edges', driver='GPKG')
    # graphs with  15–500 edges
    medium_graph_edges_gdf = gpd.GeoDataFrame(medium_graph_edges, crs=from_epsg(3879))
    medium_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='medium_graph_edges', driver='GPKG')
    # graphs with > 500 edges
    big_graph_edges_gdf = gpd.GeoDataFrame(big_graph_edges, crs=from_epsg(3879))
    big_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='big_graph_edges', driver='GPKG')
    log.info(f'graphs exported')

# 10) delete smallest subgraphs from the graph
del_edge_ids = [edge['id_ig'] for edge in small_graph_edges]
log.info(f'deleting {len(del_edge_ids)} isolated edges')
before_count = G.ecount()
G.delete_edges(del_edge_ids)
after_count = G.ecount()
del_ratio = round(100 * (before_count-after_count) / before_count, 1)
log.info(f'deleted {before_count-after_count} ({del_ratio} %) edges')

# 11) delete isolated nodes from the graph
del_node_ids = [v.index for v in G.vs.select(_degree_eq=0)]
log.info(f'deleting {len(del_node_ids)} isolated nodes')
before_count = G.vcount()
G.delete_vertices(del_node_ids)
after_count = G.vcount()
del_ratio = round(100 * (before_count-after_count) / before_count, 1)
log.info(f'deleted {before_count-after_count} ({del_ratio} %) nodes')

# check if id_ig:s need to be updated to edge attributes
mismatch_count = len([edge.index for edge in G.es if edge.attributes()['id_ig'] != edge.index])
log.info(f'invalid edge ids: {mismatch_count}')
# reassign igraph indexes to edge and node attributes
G.es['id_ig'] = [e.index for e in G.es]
G.vs['id_ig'] = [v.index for v in G.vs]
# check if id_ig:s need to be updated to edge attributes
mismatch_count = len([edge.index for edge in G.es if edge.attributes()['id_ig'] != edge.index])
log.info(f'invalid edge ids: {mismatch_count} (after re-indexing)')

# 12) export graph data to GeoDataFrames fro debugging
log.info(f'exporting final graph to {debug_igraph_gpkg} for debugging')
e_gdf = ig_utils.get_edge_gdf(G, attrs=['id_otp', 'id_ig', 'source', 'target'])
n_gdf = ig_utils.get_node_gdf(G, attrs=['index'])

if (export_final_graph_to_gpkg == True):
    e_gdf.to_file(debug_igraph_gpkg, layer='final_graph_edges', driver='GPKG')
    n_gdf.to_file(debug_igraph_gpkg, layer='final_graph_nodes', driver='GPKG')

log.info('all done')
