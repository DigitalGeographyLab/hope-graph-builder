import sys
sys.path.append('..')
import unittest
from shapely.geometry import LineString, Polygon
import pandas as pd
import geopandas as gpd
import shapely.wkt
from fiona.crs import from_epsg
from common.constants import Node, Edge
from common.logger import Logger
from otp2igraph_import.otp2igraph_import import convert_otp_graph_to_igraph

def intersects_polygon(geom: LineString, polygon: Polygon):
    if (geom.is_empty == True): return True
    return True if geom.intersects(polygon) else False

class TestCreateTestOtpGraphData(unittest.TestCase):
    
    @unittest.skip('run before')
    def test_create_test_otp_graph_data(self):
        test_area = gpd.read_file('data/test_area.geojson')['geometry'][0]

        e = pd.read_csv('data/edges.csv', sep=';')
        self.assertEqual(1282306, len(e))
        e[Edge.geometry.name] = [shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e[Edge.geometry.name]]
        e = gpd.GeoDataFrame(e, geometry=Edge.geometry.name, crs=from_epsg(4326))
        e['in_test_area'] = [intersects_polygon(line, test_area) for line in e[Edge.geometry.name]]
        e_filt = e.query('in_test_area == True').copy()
        e_filt.drop(columns=['in_test_area']).to_csv('data/test_edges.csv', sep=';')
        self.assertEqual(6314, len(e_filt))
        used_nodes = set(list(e_filt['node_orig_id'])+list(e_filt['node_dest_id']))

        n = pd.read_csv('data/nodes.csv', sep=';')
        self.assertEqual(474874, len(n))
        n['in_test_area'] = [True if id_otp in used_nodes else False for id_otp in n['id_otp']]
        n_filt = n.query('in_test_area == True').copy()
        n_filt.drop(columns=['in_test_area']).to_csv('data/test_nodes.csv', sep=';')
        self.assertEqual(3420, len(n_filt))

class TestOtp2IgraphImport(unittest.TestCase):
    
    def test_otp_2_igraph_import(self):
        result = convert_otp_graph_to_igraph(
            node_csv_file = 'data/test_nodes.csv',
            edge_csv_file = 'data/test_edges.csv',
            hma_poly_file = 'data/HMA.geojson',
            igraph_out_file = '',
            b_export_otp_data_to_gpkg = False,
            b_export_decomposed_igraphs_to_gpkg = False,
            b_export_final_graph_to_gpkg = False,
            debug_otp_graph_gpkg = None,
            debug_igraph_gpkg = None,
            log = Logger()
        )
        self.assertEqual(3702, result['edge_count'])

if __name__ == '__main__':
    unittest.main()
