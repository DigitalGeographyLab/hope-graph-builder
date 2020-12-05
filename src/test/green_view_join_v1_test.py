import sys
sys.path.append('..')
from typing import Dict, List
import pytest
from geopandas import GeoDataFrame
from igraph import Graph
from common.logger import Logger
import common.igraph as ig_utils
from common.igraph import Edge as E
from green_view_join_v1.green_view_join_v1 import (
    get_point_gvi_list_by_edge_id, load_point_gvi_gdf, get_mean_edge_point_gvi, add_mean_point_gvi)


log = Logger()

@pytest.fixture
def graph() -> Graph:
    yield ig_utils.read_graphml(r'data/test_graph.graphml')

@pytest.fixture
def edge_gdf(graph) -> GeoDataFrame:
    yield ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length])

@pytest.fixture
def point_gvi_gdf() -> GeoDataFrame:
    yield load_point_gvi_gdf(r'data/greenery_points.gpkg')

@pytest.fixture
def gvi_list_by_edge_id(edge_gdf, point_gvi_gdf) -> Dict[int, List[float]]:
    yield get_point_gvi_list_by_edge_id(log, edge_gdf, point_gvi_gdf)


def test_get_point_gvi_list_by_edges(gvi_list_by_edge_id):
    assert isinstance(gvi_list_by_edge_id, dict)
    assert len(gvi_list_by_edge_id) == 1808
    for edge_id, gvi_list in gvi_list_by_edge_id.items():
        assert isinstance(edge_id, int)
        assert isinstance(gvi_list, list)
        assert len(gvi_list) > 0
        for gvi in gvi_list:
            assert isinstance(gvi, float)


def test_calculate_mean_edge_point_gvi():
    gvi_list = [0.5, 1, 0]
    m_gvi = get_mean_edge_point_gvi(gvi_list, 10)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(gvi_list, 5)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(gvi_list, 40)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(gvi_list, 70)
    assert m_gvi == 0.5
    m_gvi = get_mean_edge_point_gvi(gvi_list, 80)
    assert m_gvi is None
    

def test_add_mean_point_gvi_to_edge_gdf(edge_gdf, gvi_list_by_edge_id):
    edge_gdf_gvi = add_mean_point_gvi(log, gvi_list_by_edge_id, edge_gdf)
    mean_p_GVIs = list(edge_gdf_gvi['mean_p_GVI'])
    assert len(mean_p_GVIs) == len(edge_gdf)
    GVIs = [gvi for gvi in mean_p_GVIs if gvi]
    assert len(GVIs) == 3702
    for gvi in GVIs:
        assert isinstance(gvi, float)
