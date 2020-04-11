import geopandas as gpd
import igraph as ig
from fiona.crs import from_epsg

def get_edge_dicts(G: ig.Graph, attrs: list = ['geometry']) -> list:
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

def get_edge_gdf(G: ig.Graph, length: bool = False, id_attr: str = 'name', attrs: list = ['geometry'], epsg: int = 4326) -> gpd.GeoDataFrame:
    """Returns edges of a graph as pandas GeoDataFrame. 
    """
    edge_dicts = get_edge_dicts(G, attrs=attrs)
    ids = [ed[id_attr] for ed in edge_dicts]
    gdf = gpd.GeoDataFrame(edge_dicts, index=ids, crs=from_epsg(epsg))
    return gdf.drop(columns=[id_attr])
