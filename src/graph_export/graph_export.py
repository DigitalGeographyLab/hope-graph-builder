import sys
sys.path.append('..')
import common.igraph as ig_utils
from common.igraph import Edge as E, Node as N
import utils


graph_name = 'kumpula'

graph = ig_utils.read_graphml(f'graph_in/{graph_name}.graphml')
out_graph = f'graph_out/{graph_name}.graphml'
out_graph_research = f'graph_out/{graph_name}_r.graphml'
out_geojson_noise = f'graph_out/{graph_name}_noise.geojson'
out_geojson = f'graph_out/{graph_name}.geojson'

out_node_attrs = [N.geometry]
out_edge_attrs = [
    E.id_ig, E.uv, E.id_way, E.geometry, E.geom_wgs, 
    E.length, E.length_b, E.noises, E.gvi
]

def set_biking_lengths(graph, edge_gdf):
    for edge in edge_gdf.itertuples():
        length = getattr(edge, E.length.name)
        biking_length = length * getattr(edge, E.bike_safety_factor.name) if length != 0.0 else 0.0
        graph.es[getattr(edge, E.id_ig.name)][E.length_b.value] = round(biking_length, 3)

def set_uv(graph, edge_gdf):
    edge_gdf['uv'] = edge_gdf.apply(lambda x: (x['source'], x['target']), axis=1)
    graph.es[E.uv.value] = list(edge_gdf['uv'])

def set_way_ids(graph, edge_gdf):
    edge_gdf['way_id'] = edge_gdf.apply(lambda x: str(round(x['length'], 1))+str(sorted(x['uv'])), axis=1)
    way_ids = list(edge_gdf['way_id'].unique())
    way_ids_d = { way_id: idx for idx, way_id in enumerate(way_ids) }
    edge_gdf['way_id'] = [way_ids_d[way_id] for way_id in edge_gdf['way_id']]
    graph.es[E.id_way.value] = list(edge_gdf['way_id'])

edge_gdf = ig_utils.get_edge_gdf(
    graph, 
    attrs=[E.id_ig, E.length, E.bike_safety_factor], 
    ig_attrs=['source', 'target']
)

set_biking_lengths(graph, edge_gdf)
set_uv(graph, edge_gdf)
set_way_ids(graph, edge_gdf)

# create geojson for vector tiles
geojson = utils.create_geojson(graph)
utils.write_geojson(geojson, out_geojson, overwrite=True, id_attr=True)
utils.write_geojson(geojson, out_geojson_noise, overwrite=True, db_prop=True)

# set combined GVI to GVI attribute
graph.es[E.gvi.value] = list(graph.es[E.gvi_comb_gsv_veg.value])
ig_utils.export_to_graphml(graph, out_graph, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)

# for research use, set combined GVI that omits low vegetation to GVI attribute and export graph
graph.es[E.gvi.value] = list(graph.es[E.gvi_comb_gsv_high_veg.value])
ig_utils.export_to_graphml(graph, out_graph_research, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)

# TODO export subset of the graph by the extent of Helsinki
