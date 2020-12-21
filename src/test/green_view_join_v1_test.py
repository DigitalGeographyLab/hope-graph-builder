import sys
sys.path.append('..')
sys.path.append('../green_view_join_v1')
from typing import Dict, List
import pytest
from geopandas import GeoDataFrame
from igraph import Graph
from common.logger import Logger
import common.igraph as ig_utils
from common.igraph import Edge as E
from green_view_join_v1.green_view_join_v1 import (
    get_point_gvi_list_by_way_id, load_point_gvi_gdf, get_mean_edge_point_gvi, get_mean_point_gvi_by_way_id)


log = Logger()

@pytest.fixture
def graph() -> Graph:
    yield ig_utils.read_graphml(r'data/test_graph.graphml')

@pytest.fixture
def edge_gdf(graph) -> GeoDataFrame:
    gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length])
    # test graph does not have id_way attribute so let's "add" one
    yield gdf.rename(columns={E.id_ig.name: E.id_way.name})

@pytest.fixture
def point_gvi_gdf() -> GeoDataFrame:
    yield load_point_gvi_gdf(r'data/greenery_points.gpkg')

@pytest.fixture
def gvi_list_by_way_id(edge_gdf, point_gvi_gdf) -> Dict[int, List[float]]:
    yield get_point_gvi_list_by_way_id(log, edge_gdf, point_gvi_gdf)


def test_get_point_gvi_list_by_edges(gvi_list_by_way_id):
    assert isinstance(gvi_list_by_way_id, dict)
    assert len(gvi_list_by_way_id) == 1808
    for way_id, gvi_list in gvi_list_by_way_id.items():
        assert isinstance(way_id, int)
        assert isinstance(gvi_list, list)
        assert len(gvi_list) > 0
        for gvi in gvi_list:
            assert isinstance(gvi, float)


def test_calculate_mean_edge_point_gvi():
    gvi_list = [0.5, 1, 0]
    m_gvi = get_mean_edge_point_gvi(10, gvi_list)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(5, gvi_list)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(40, gvi_list)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(70, gvi_list)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(80, gvi_list)
    assert m_gvi is None
