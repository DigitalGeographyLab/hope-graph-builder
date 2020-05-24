import sys
sys.path.append('..')
sys.path.append('../noise_graph_join')
import os
import time
import fiona
import unittest
import numpy as np
import pandas as pd
import geopandas as gpd
import noise_graph_join.utils as utils
import common.igraph as ig_utils
from noise_graph_join import noise_graph_join
from common.schema import Edge as E
from common.logger import Logger
from shapely.geometry import LineString, Polygon, Point, GeometryCollection

log = Logger()

class TestNoiseGraphJoinUtils(unittest.TestCase):

    def test_calculate_point_sampling_distances(self):
        sampling_points = utils.get_point_sampling_distances(5)
        self.assertEqual(len(sampling_points), 5)
        self.assertEqual(sampling_points[0], (1/5)/2)
        self.assertEqual(sampling_points[1], (1/5)/2 + 1/5)
        self.assertEqual(sampling_points[4], (1/5)/2 + 4 * (1/5))
        sampling_points = utils.get_point_sampling_distances(1)
        self.assertEqual(sampling_points[0], 0.5)

    def test_add_sampling_points(self):
        graph = ig_utils.read_graphml('data/test_graph.graphml')
        gdf = ig_utils.get_edge_gdf(graph)
        # start_time = time.time()
        gdf = utils.add_sampling_points_to_gdf(gdf, 2)
        # log.duration(start_time, 'added sampling points')
        sampling_points_list = list(gdf['sampling_points'])
        self.assertEqual(len([sps for sps in sampling_points_list if sps != None]), 3522)
        self.assertEqual(len([sps for sps in sampling_points_list if sps == None]), 180)
        # test that all sample points are on the line geometries
        for edge in gdf.itertuples():
            sampling_points = getattr(edge, 'sampling_points')
            if (sampling_points == None): continue
            line_geom = getattr(edge, 'geometry')
            for sp in sampling_points:
                self.assertAlmostEqual(sp.distance(line_geom), 0, 5)

        # validate sampling point gdf (exploaded from edge gdf with sampling points)
        sampling_gdf = utils.explode_sampling_point_gdf(gdf, 'sampling_points')
        self.assertGreater(len(sampling_gdf), len(gdf))
        self.assertEqual(len(sampling_gdf), 58554)
        # check that the total representative length of each set of sampling points equals the length of the respective edge
        sps_by_edge = sampling_gdf.groupby('edge_id')
        for edge in gdf.itertuples():
            if (edge.sampling_points != None):
                edge_sps = sps_by_edge.get_group(edge.Index)
                sampling_length_sum = edge_sps['sample_len'].sum()            
                self.assertAlmostEqual(sampling_length_sum, edge.geometry.length, 5)

    def test_get_sampling_points_around_point(self):
        point = Point(25501668.9, 6684943.1)
        sps = utils.get_sampling_points_around(point, 40, count=20)
        self.assertEqual(len(sps), 20)
        for sp in sps:
            self.assertAlmostEqual(sp.distance(point), 40, 1)
        distances_between = [sp.distance(point) for point in sps]
        self.assertAlmostEqual(np.std(distances_between), 24.812, 3)

class TestNoiseGraphJoin(unittest.TestCase):

    def test_edge_noise_join(self):
        graph = ig_utils.read_graphml('data/test_graph.graphml')
        edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length])
        edge_gdf['edge_id'] = edge_gdf.index
        # read noise data
        noise_layer_names = [layer for layer in fiona.listlayers('data/noise_data_processed.gpkg')]
        noise_layers = { name: gpd.read_file('data/noise_data_processed.gpkg', layer=name) for name in noise_layer_names }
        noise_layers = { name: gdf.rename(columns={'db_low':name}) for name, gdf in noise_layers.items() }

        # read nodata zone: narrow area between noise surfaces of different municipalities
        nodata_layer = gpd.read_file('data/extents.gpkg', layer='municipal_boundaries')

        edge_noises = noise_graph_join.noise_graph_join(
            log = log,
            edge_gdf=edge_gdf,
            sampling_interval = 3,
            noise_layers = noise_layers,
            nodata_layer = nodata_layer
        )

        self.assertEqual(edge_noises['edge_id'].nunique(), 3522)

        edge_noises_df = pd.merge(edge_gdf, edge_noises, how='inner', on='edge_id')
        edge_noises_df['total_noise_len'] = [round(sum(noises.values()), 4) for noises in edge_noises_df['noises']]

        def validate_edge_noises(row):
            self.assertLessEqual(round(row['total_noise_len'], 1), round(row['length'], 1))
        
        edge_noises_df.apply(lambda row: validate_edge_noises(row), axis=1)

        self.assertAlmostEqual(edge_noises_df['total_noise_len'].mean(), 33.20, 2)
        

if (__name__ == '__main__'):
    unittest.main()
