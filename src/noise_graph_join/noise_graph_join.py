import sys
sys.path.append('..')
from common.logger import Logger
import utils as utils
import common.igraph as ig_utils
from common.schema import Edge as E, Node as N

def noise_graph_join(log: Logger, b_debug: bool, graph_file: str, noise_gpkg: str, sampling_interval: float):
    graph = ig_utils.read_graphml(graph_file)
    log.info(f'read graph of {graph.ecount()} edges')
    gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig])
    gdf = utils.add_sampling_points_to_gdf(gdf, sampling_interval=3)
    point_gdf = utils.explode_sampling_point_gdf(gdf)
    log.info(f'created {len(point_gdf)} sampling points ({round(len(point_gdf)/graph.ecount(),2)} per edge)')

    if (b_debug == True):
        log.info('exporting edges and sampling points for debugging')
        gdf.drop(columns=['sampling_points']).to_file('debug/noise_join_debug.gpkg', layer='graph_edges', driver='GPKG')
        point_gdf.to_file('debug/noise_join_debug.gpkg', layer='sampling_points', driver='GPKG')

if (__name__ == '__main__'):
    noise_graph_join(
        log = Logger(printing=True, log_file='noise_graph_join.log', level='info'),
        b_debug = True,
        graph_file = 'data/test_graph.graphml',
        noise_gpkg = 'data/noise_data_processed.gpkg',
        sampling_interval = 3
    )
