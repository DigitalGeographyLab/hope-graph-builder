import sys
sys.path.append('..')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import numpy as np
import pandas as pd
import geopandas as gpd
import igraph as ig
import shapely.wkt
from fiona.crs import from_epsg
from utils.logger import Logger

export_to_gpkg: bool = False
otp_graph_gpkg = 'otp_graph_data/otp_graph_features.gpkg'
log = Logger(printing=True, log_file='otp2igraph_import.log', level='info')

# 1) read OTP graph data from CSV files

e = pd.read_csv('otp_graph_data/edges.csv', sep=';')
e = e.rename(columns={'id': 'id_otp'})
log.info(f'read {len(e.index)} edges')
log.debug(f'edge column types: {e.dtypes}')
log.debug(f'edges head: {e.head()}')
e['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else None for geom in e['geometry']]

n = pd.read_csv('otp_graph_data/nodes.csv', sep=';')
n = n.rename(columns={'id': 'id_otp'})
log.info(f'read {len(n.index)} nodes')
log.debug(f'node column types: {n.dtypes}')
log.debug(f'nodes head: {n.head()}')
n['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else None for geom in n['geometry']]

if (export_to_gpkg == True):
    log.info('writing graph data to gpkg')
    e_gdf = gpd.GeoDataFrame(e, geometry='geometry', crs=from_epsg(4326))
    e_gdf.to_file(otp_graph_gpkg, layer='edges', driver='GPKG')
    log.info(f'exported edges to {otp_graph_gpkg} (layer=edges)')
    n_gdf = gpd.GeoDataFrame(n, geometry='geometry', crs=from_epsg(4326))
    n_gdf.to_file(otp_graph_gpkg, layer='nodes', driver='GPKG')
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
n['id_ig'] = np.arange(len(n))
ids_otp_ig = {}
ids_ig_otp = {}
for node in n.itertuples():
    ids_otp_ig[getattr(node, 'id_otp')] = getattr(node, 'id_ig')
    ids_ig_otp[getattr(node, 'id_ig')] = getattr(node, 'id_otp')
    
# 4) add nodes to graph
log.info('adding nodes to graph')
G = ig.Graph()
G.add_vertices(len(n.index))
G.vs['id_otp'] = list(n['id_otp'])
G.vs['geometry'] = list(n['geometry'])

# 5) add edges to graph
log.info('adding edges to graph')

def get_ig_uv(edge):
    return (ids_otp_ig[edge['nodeOrigId']], ids_otp_ig[edge['nodeDestId']])

e_filt['uv_ig'] = e_filt.apply(lambda row: get_ig_uv(row), axis=1)
G.add_edges(list(e_filt['uv_ig']))
G.es['id_otp'] = list(e_filt['id_otp'])
G.es['uv_ig'] = list(e_filt['uv_ig'])
G.es['geometry'] = list(e_filt['geometry'])
# TODO: add rest of the edge attributes

# 6) 

# create igraph

# TODO: build igraph graph

# TODO: clean graph from subgraphs (use decompose method of the graph)

