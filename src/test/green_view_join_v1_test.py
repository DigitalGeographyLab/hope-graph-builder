import sys
sys.path.append('..')
sys.path.append('../green_view_join_v1')
from typing import Dict, List
import pytest
import pandas as pd
from shapely.geometry import LineString
from geopandas import GeoDataFrame
from igraph import Graph
from common.logger import Logger
import common.igraph as ig_utils
from common.igraph import Edge as E
from green_view_join_v1.green_view_join_v1 import (
    get_point_gvi_list_by_way_id, load_point_gvi_gdf, 
    get_mean_edge_point_gvi, get_mean_point_gvi_by_way_id, 
    update_gvi_attributes_to_graph)


log = Logger()

@pytest.fixture
def graph() -> Graph:
    g = ig_utils.read_graphml(r'data/test_graph.graphml')
    g.es[E.id_way.value] = list(g.es[E.id_ig.value])
    yield g

@pytest.fixture
def edge_gdf(graph) -> GeoDataFrame:
    yield ig_utils.get_edge_gdf(graph, attrs=[E.id_way, E.length])

@pytest.fixture
def point_gvi_gdf() -> GeoDataFrame:
    yield load_point_gvi_gdf(r'data/greenery_points.gpkg')

@pytest.fixture
def gvi_list_by_way_id(edge_gdf, point_gvi_gdf) -> Dict[int, List[float]]:
    yield get_point_gvi_list_by_way_id(log, edge_gdf, point_gvi_gdf)

@pytest.fixture
def mean_point_gvi_by_way_id(gvi_list_by_way_id, edge_gdf) -> Dict[int, List[float]]:
    yield get_mean_point_gvi_by_way_id(log, gvi_list_by_way_id, edge_gdf)

@pytest.fixture
def low_veg_share_by_way_id() -> Dict[int, List[float]]:
    df = pd.read_csv(r'data/edge_subset_low_veg_shares.csv')
    way_ids = list(df['id_way'])
    low_veg_shares = list(df['low_veg_share'])
    yield dict(zip(way_ids, low_veg_shares))

@pytest.fixture
def high_veg_share_by_way_id() -> Dict[int, List[float]]:
    df = pd.read_csv(r'data/edge_subset_high_veg_shares.csv')
    way_ids = list(df['id_way'])
    high_veg_shares = list(df['high_veg_share'])
    yield dict(zip(way_ids, high_veg_shares))


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


def test_mean_get_mean_point_gvi_by_way_id(mean_point_gvi_by_way_id):
    for way_id, mean_point_gvi in mean_point_gvi_by_way_id.items():
        assert isinstance(way_id, int)
        assert isinstance(mean_point_gvi, float)
    assert len(mean_point_gvi_by_way_id) == 1718


def test_join_gvi_attributes_to_graph(
    graph,
    mean_point_gvi_by_way_id,
    low_veg_share_by_way_id,
    high_veg_share_by_way_id
):
    updated = update_gvi_attributes_to_graph(
        graph,
        mean_point_gvi_by_way_id,
        low_veg_share_by_way_id,
        high_veg_share_by_way_id
    )

    for e in updated.es:
        attrs = e.attributes()
        expected_type = float if isinstance(attrs[E.geometry.value], LineString) else type(None)
        assert isinstance(attrs[E.gvi_gsv.value], (float, type(None)))
        assert isinstance(attrs[E.gvi_low_veg_share.value], expected_type)
        assert isinstance(attrs[E.gvi_high_veg_share.value], expected_type)
        assert isinstance(attrs[E.gvi_comb_gsv_veg.value], expected_type)
        assert isinstance(attrs[E.gvi_comb_gsv_high_veg.value], expected_type)

    gvi_comb_gsv_veg = [gvi for gvi in list(updated.es[E.gvi_comb_gsv_veg.value]) if gvi]
    gvi_comb_gsv_high_veg = [gvi for gvi in list(updated.es[E.gvi_comb_gsv_high_veg.value]) if gvi]
    
    assert len(gvi_comb_gsv_veg) == 3456
    assert len(gvi_comb_gsv_high_veg) == 3240
    assert max(gvi_comb_gsv_veg) == 0.9
    assert max(gvi_comb_gsv_high_veg) == 0.85
    assert min(gvi_comb_gsv_veg) == 0.01
    assert min(gvi_comb_gsv_high_veg) == 0.01
