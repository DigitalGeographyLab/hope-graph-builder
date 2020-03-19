import pandas as pd
import geopandas as gpd
import shapely.wkt
from fiona.crs import from_epsg
from utils.logger import Logger
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

export_to_gpkg: bool = True
otp_graph_gpkg = 'otp_graph_data/otp_graph_features.gpkg'
log = Logger(printing=True, log_file='load_inspect_otp_graph.log')

edges = pd.read_csv('otp_graph_data/edges.csv', sep=';')
edges['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else None for geom in edges['geometry']]
log.info(f'read {len(edges.index)} edges')

nodes = pd.read_csv('otp_graph_data/nodes.csv', sep=';')
nodes['geometry'] = [shapely.wkt.loads(geom) if isinstance(geom, str) else None for geom in nodes['geometry']]
log.info(f'read {len(nodes.index)} nodes')

if (export_to_gpkg == True):
    log.info('writing graph data to gpkg')
    edges = gpd.GeoDataFrame(edges, geometry='geometry', crs=from_epsg(4326))
    edges.to_file(otp_graph_gpkg, layer='edges', driver='GPKG')
    log.info(f'exported edges to {otp_graph_gpkg} (layer=edges)')
    nodes = gpd.GeoDataFrame(nodes, geometry='geometry', crs=from_epsg(4326))
    nodes.to_file(otp_graph_gpkg, layer='nodes', driver='GPKG')
    log.info(f'exported nodes to {otp_graph_gpkg} (layer=nodes)')
