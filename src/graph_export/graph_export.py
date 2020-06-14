import sys
sys.path.append('..')
import common.igraph as ig_utils
from common.igraph import Edge as E, Node as N

graph = ig_utils.read_graphml('data/hma.graphml')
out_graph = 'out_graph/hma.graphml'

out_node_attrs = [N.geometry]
out_edge_attrs = [E.id_ig, E.uv, E.geometry, E.geom_wgs, E.length, E.length_b, E.noises, E.noise_source]

def set_biking_lengths(graph, edge_gdf):
    # TODO use walking speed when allows_biking=False or traversable_biking=False
    for edge in edge_gdf.itertuples():
        length = getattr(edge, E.length.name)
        biking_length = length * getattr(edge, E.bike_safety_factor.name) if length != 0.0 else 0.0
        graph.es[getattr(edge, E.id_ig.name)][E.length_b.value] = round(biking_length, 4)

def set_uv(graph, edge_gdf):
    for edge in edge_gdf.itertuples():
        source = getattr(edge, 'source')
        target = getattr(edge, 'target')
        graph.es[getattr(edge, E.id_ig.name)][E.uv.value] = (source, target)

edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length, E.bike_safety_factor], ig_attrs=['source', 'target'])

set_biking_lengths(graph, edge_gdf)
set_uv(graph, edge_gdf)

ig_utils.export_to_graphml(graph, out_graph, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)
