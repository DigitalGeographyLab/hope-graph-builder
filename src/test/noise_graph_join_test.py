import sys
sys.path.append('..')
import os
import time
import unittest
import noise_graph_join.utils as utils
import common.igraph as ig_utils
from common.logger import Logger
from shapely.geometry import LineString, Polygon, Point, GeometryCollection

log = Logger(printing=True)

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
        sampling_gdf = utils.explode_sampling_point_gdf(gdf)
        self.assertGreater(len(sampling_gdf), len(gdf))
        self.assertEqual(len(sampling_gdf), 58554)
        # check that the total representative length of each set of sampling points equals the length of the respective edge
        sps_by_edge = sampling_gdf.groupby('edge_id')
        for edge in gdf.itertuples():
            if (edge.sampling_points != None):
                edge_sps = sps_by_edge.get_group(edge.Index)
                sampling_length_sum = edge_sps['sample_len'].sum()            
                self.assertAlmostEqual(sampling_length_sum, edge.geometry.length, 5)

# class TestNoiseGraphJoin(unittest.TestCase):

if (__name__ == '__main__'):
    unittest.main()
