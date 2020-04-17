from enum import Enum
from typing import List, Set, Dict, Tuple
import geopandas as gpd
import igraph as ig
from igraph import Graph
from fiona.crs import from_epsg
from common.constants import Node, Edge

def get_edge_dicts(G: Graph, attrs: List[Enum] = [Edge.geometry]) -> list:
    """Returns list of all edges of a graph as dictionaries with the specified attributes. 
    """
    edge_dicts = []
    for edge in G.es:
        edge_attrs = edge.attributes()
        edge_dict = {}
        for attr in attrs:
            if (attr.value in edge_attrs):
                edge_dict[attr.name] = edge_attrs[attr.value]
        edge_dicts.append(edge_dict)
    return edge_dicts

def get_edge_gdf(G: Graph, id_attr: Enum = None, attrs: List[Enum] = [], ig_attrs: List[str] = [], geom_attr: Enum = Edge.geometry, epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns edges of a graph as pandas GeoDataFrame. 
    """
    edge_dicts = []
    ids = []
    for edge in G.es:
        edge_dict = {}
        edge_attrs = edge.attributes()
        ids.append(edge_attrs[id_attr.value] if id_attr is not None else edge.index)
        edge_dict[geom_attr.name] = edge_attrs[geom_attr.value]
        for attr in attrs:
            if (attr.value in edge_attrs):
                edge_dict[attr.name] = edge_attrs[attr.value]
        for attr in ig_attrs:
            if (hasattr(edge, attr)):
                edge_dict[attr] = getattr(edge, attr)
        edge_dicts.append(edge_dict)

    return gpd.GeoDataFrame(edge_dicts, index=ids, crs=from_epsg(epsg))

def get_node_gdf(G: Graph, id_attr: Enum = None, attrs: List[Enum] = [], ig_attrs: List[str] = [], geom_attr: Enum = Node.geometry, epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns nodes of a graph as pandas GeoDataFrame. 
    """
    node_dicts = []
    ids = []
    for node in G.vs:
        node_dict = {}
        node_attrs = node.attributes()
        ids.append(node_attrs[id_attr.value] if id_attr is not None else node.index)
        node_dict[geom_attr.name] = node_attrs[geom_attr.value]
        for attr in attrs:
            if(attr.value in node_attrs):
                node_dict[attr.name] = node_attrs[attr.value]
        for attr in ig_attrs:
            if (hasattr(node, attr)):
                node_dict[attr] = getattr(node, attr)
        node_dicts.append(node_dict)

    return gpd.GeoDataFrame(node_dicts, index=ids, crs=from_epsg(epsg))
