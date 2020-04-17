import enum

class Node(enum.Enum):
   version = 1.0
   id_ig = 'ii'
   id_otp = 'io'
   name_otp = 'no'
   geometry = 'geom'
   geom_wgs = 'geom_wgs'
   traversable_walking = 'b_tw'
   traversable_biking = 'b_tb'
   traffic_light = 'tl'

class Edge(enum.Enum):
   version = 1.0
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
