import geopandas as gpd
import igraph as ig
from igraph import Graph
from fiona.crs import from_epsg

def get_edge_dicts(G: Graph, attrs: list = ['geometry']) -> list:
    """Returns list of all edges of a graph as dictionaries with the specified attributes. 
    """
    edge_dicts = []
    for edge in G.es:
        edge_attrs = edge.attributes()
        edge_dict = {}
        for attr in attrs:
            if (attr in edge_attrs):
                edge_dict[attr] = edge_attrs[attr]
        edge_dicts.append(edge_dict)
    return edge_dicts

def get_edge_gdf(G: Graph, id_attr: str = None, attrs: list = [], geom_attr: str = 'geometry', epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns edges of a graph as pandas GeoDataFrame. 
    """
    edge_dicts = []
    ids = []
    for edge in G.es:
        edge_dict = {}
        edge_attrs = edge.attributes()
        ids.append(edge_attrs[id_attr] if id_attr is not None else edge.index)
        edge_dict['geometry'] = edge_attrs[geom_attr]
        for attr in attrs:
            if (attr in edge_attrs):
                edge_dict[attr] = edge_attrs[attr]
            elif (hasattr(edge, attr)):
                edge_dict[attr] = getattr(edge, attr)
        edge_dicts.append(edge_dict)

    return gpd.GeoDataFrame(edge_dicts, index=ids, crs=from_epsg(epsg))

def get_node_gdf(G: Graph, id_attr: str = None, attrs: list = [], geom_attr: str = 'geometry', epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns nodes of a graph as pandas GeoDataFrame. 
    """
    node_dicts = []
    ids = []
    for node in G.vs:
        node_dict = {}
        node_attrs = node.attributes()
        ids.append(node_attrs[id_attr] if id_attr is not None else node.index)
        node_dict['geometry'] = node_attrs[geom_attr]
        for attr in attrs:
            if(attr in node_attrs):
                node_dict[attr] = node_attrs[attr]
            elif (hasattr(node, attr)):
                node_dict[attr] = getattr(node, attr)
        node_dicts.append(node_dict)

    return gpd.GeoDataFrame(node_dicts, index=ids, crs=from_epsg(epsg))
