import enum
import ast
from shapely import wkt

version = 1.0

class Node(enum.Enum):
   id_ig = 'ii'
   id_otp = 'io'
   name_otp = 'no'
   geometry = 'geom'
   geom_wgs = 'geom_wgs'
   traversable_walking = 'b_tw'
   traversable_biking = 'b_tb'
   traffic_light = 'tl'

class Edge(enum.Enum):
   id_ig = 'ii'
   id_otp = 'io'
   name_otp = 'no'
   geometry = 'geom'
   geom_wgs = 'geom_wgs'
   length = 'l'
   edge_class = 'ec'
   street_class = 'sc'
   is_stairs = 'b_st'
   is_no_thru_traffic = 'b_ntt'
   allows_walking = 'b_aw'
   allows_biking = 'b_ab'
   traversable_walking = 'b_tw'
   traversable_biking = 'b_tb'
   bike_safety_factor = 'bsf'
   noises = 'n'
   noise_sources = 'ns'


def to_str(value):
    return str(value)
def to_int(value):
    return int(value)
def to_float(value):
    return float(value)
def to_geom(value):
    return wkt.loads(value)
def to_bool(value):
   return ast.literal_eval(value)

edge_attr_converters = {
    Edge.id_ig: to_int,
    Edge.id_otp: to_str,
    Edge.name_otp: to_str,
    Edge.geometry: to_geom,
    Edge.geom_wgs: to_geom,
    Edge.length: to_float,
    Edge.edge_class: to_str,
    Edge.street_class: to_str,
    Edge.is_stairs: to_bool,
    Edge.is_no_thru_traffic: to_bool,
    Edge.allows_walking: to_bool,
    Edge.allows_biking: to_bool,
    Edge.traversable_walking: to_bool,
    Edge.traversable_biking: to_bool,
    Edge.bike_safety_factor: to_float,
}

node_attr_converters = {
    Node.id_ig: to_int,
    Node.id_otp: to_str,
    Node.name_otp: to_str,
    Node.geometry: to_geom,
    Node.geom_wgs: to_geom,
    Node.traversable_walking: to_bool,
    Node.traversable_biking: to_bool,
    Node.traffic_light: to_bool,
}
