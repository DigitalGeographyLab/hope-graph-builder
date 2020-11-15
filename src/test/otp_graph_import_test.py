import sys
sys.path.append('..')
import os
import unittest
from shapely.geometry import LineString, Polygon, Point, GeometryCollection
import pandas as pd
import geopandas as gpd
import shapely.wkt
from pyproj import CRS
from common.igraph import Node, Edge
from common.logger import Logger
import common.igraph as ig_utils
from otp_graph_import.otp_graph_import import convert_otp_graph_to_igraph

class TestCreateTestOtpGraphData(unittest.TestCase):

    def intersects_polygon(self, geom: LineString, polygon: Polygon):
        if (geom.is_empty == True): return True
        return True if geom.intersects(polygon) else False
    
    @unittest.skip('run before')
    def test_create_test_otp_graph_data(self):
        test_area = gpd.read_file('data/kumpula_aoi.geojson')['geometry'][0]

        e = pd.read_csv('data/edges.csv', sep=';')
        self.assertEqual(len(e), 1282306)
        e[Edge.geometry.name] = [shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e[Edge.geometry.name]]
        e = gpd.GeoDataFrame(e, geometry=Edge.geometry.name, crs=CRS.from_epsg(4326))
        e['in_test_area'] = [self.intersects_polygon(line, test_area) for line in e[Edge.geometry.name]]
        e_filt = e.query('in_test_area == True').copy()
        e_filt.drop(columns=['in_test_area']).to_csv('data/kumpula_edges.csv', sep=';')
        used_nodes = set(list(e_filt['node_orig_id'])+list(e_filt['node_dest_id']))

        n = pd.read_csv('data/nodes.csv', sep=';')
        n['in_test_area'] = [True if id_otp in used_nodes else False for id_otp in n['id_otp']]
        n_filt = n.query('in_test_area == True').copy()
        n_filt.drop(columns=['in_test_area']).to_csv('data/kumpula_nodes.csv', sep=';')
        self.assertEqual(len(n_filt), 8564)

class TestOtp2IgraphImport(unittest.TestCase):
    
    @classmethod
    def tearDownClass(cls):
        os.remove('temp/test_graph.graphml')

    def test_otp_2_igraph_import(self):
        graph = convert_otp_graph_to_igraph(
            node_csv_file = 'data/test_nodes.csv',
            edge_csv_file = 'data/test_edges.csv',
            hma_poly_file = 'data/HMA.geojson',
            igraph_out_file = 'temp/test_graph.graphml',
            b_export_otp_data_to_gpkg = False,
            b_export_decomposed_igraphs_to_gpkg = False,
            b_export_final_graph_to_gpkg = False,
            debug_otp_graph_gpkg = None,
            debug_igraph_gpkg = None,
            log = Logger()
        )
        self.assertEqual(graph.ecount(), 3702)
        self.assertEqual(graph.vcount(), 1328)
    
    def test_read_igraph(self):
        graph = ig_utils.read_graphml('temp/test_graph.graphml', log=Logger(printing=True))
        self.assertEqual(graph.ecount(), 3702)
        self.assertEqual(graph.vcount(), 1328)
        attr_names = list(graph.vs[0].attributes().keys())
        for attr in attr_names:
            self.assertIn(attr, [e.value for e in Node], 'no unknown node attributes allowed')
        attr_names = list(graph.es[0].attributes().keys())
        for attr in attr_names:
            self.assertIn(attr, [e.value for e in Edge], 'no unknown edge attributes allowed')
        for n in graph.vs:
            attrs = n.attributes()
            self.assertEqual(attrs[Node.id_ig.value], n.index)
            self.assertIsInstance(attrs[Node.id_ig.value], int)
            self.assertIsInstance(attrs[Node.id_otp.value], str)
            self.assertIsInstance(attrs[Node.name_otp.value], str)
            self.assertIsInstance(attrs[Node.geometry.value], Point)
            self.assertIsInstance(attrs[Node.geom_wgs.value], Point)
            self.assertIsInstance(attrs[Node.traversable_walking.value], bool)
            self.assertIsInstance(attrs[Node.traversable_biking.value], bool)
            self.assertIsInstance(attrs[Node.traffic_light.value], bool)
        for e in graph.es:
            attrs = e.attributes()
            self.assertEqual(attrs[Edge.id_ig.value], e.index)
            self.assertIsInstance(attrs[Edge.id_ig.value], int)
            self.assertIsInstance(attrs[Edge.id_otp.value], str)
            self.assertIsInstance(attrs[Edge.name_otp.value], str)
            self.assertIsInstance(attrs[Edge.geometry.value], (LineString, GeometryCollection))
            self.assertIsInstance(attrs[Edge.geom_wgs.value], (LineString, GeometryCollection))
            self.assertIsInstance(attrs[Edge.length.value], float)
            self.assertIsInstance(attrs[Edge.edge_class.value], str)
            self.assertIsInstance(attrs[Edge.street_class.value], str)
            self.assertIsInstance(attrs[Edge.is_stairs.value], bool)
            self.assertIsInstance(attrs[Edge.is_no_thru_traffic.value], bool)
            self.assertIsInstance(attrs[Edge.allows_walking.value], bool)
            self.assertIsInstance(attrs[Edge.allows_biking.value], bool)
            self.assertIsInstance(attrs[Edge.traversable_walking.value], bool)
            self.assertIsInstance(attrs[Edge.traversable_biking.value], bool)
            self.assertIsInstance(attrs[Edge.bike_safety_factor.value], float)

    def test_graph_to_gdf(self):
        graph = ig_utils.read_graphml('data/test_graph.graphml', log=Logger(printing=True))
        # test read graph to wgs gdf
        gdf = ig_utils.get_edge_gdf(
            graph, 
            id_attr=Edge.id_ig, 
            attrs=[Edge.length], 
            geom_attr=Edge.geom_wgs)
        gdf['geom_length'] = [geom.length for geom in gdf[Edge.geom_wgs.name]]
        self.assertAlmostEqual(gdf['geom_length'].mean(), 0.000429, 6)
        # test read to projected gdf
        gdf = ig_utils.get_edge_gdf(
            graph, 
            id_attr=Edge.id_ig, 
            attrs=[Edge.length], 
            geom_attr=Edge.geometry)
        gdf['geom_length'] = [geom.length for geom in gdf[Edge.geometry.name]]
        self.assertAlmostEqual(gdf['geom_length'].mean(), 31.65, 2)


if (__name__ == '__main__'):
    unittest.main()
