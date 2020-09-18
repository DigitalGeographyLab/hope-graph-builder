from typing import List, Dict
import os
import igraph as ig
import json
import common.igraph as ig_utils
from shapely.geometry import Point, LineString
from common.igraph import Edge as E

def __get_total_noises_len(noises: Dict[int, float]) -> float:
    """Returns a total length of exposures to all noise levels.
    """
    if (not noises):
        return 0.0
    else:
        return round(sum(noises.values()), 3)

def __estimate_db_40_exp(noises: dict, length: float) -> float:
    if (length == 0.0): return 0.0
    total_db_length = __get_total_noises_len(noises) if noises else 0.0
    return round(length - total_db_length, 2)

def __update_db_40_exp(noises: dict, length: float) -> dict:
    if not isinstance(noises, dict):
        raise ValueError('noises should be dictionary')
    noises_copy = dict(noises)
    db_40_exp = __estimate_db_40_exp(noises, length)
    if db_40_exp:
        noises_copy[40] = db_40_exp
    return noises_copy

def __get_mean_noise_level(noises: dict, length: float) -> float:
    """Returns a mean noise level based on noise exposures weighted by the contaminated distances to different noise levels.
    """
    # estimate mean dB of 5 dB range to be min dB + 2.5 dB
    sum_db = sum([(db + 2.5) * length for db, length in noises.items()])
    mean_db = sum_db/length
    return round(mean_db, 1)

def __get_noise_range(db: float) -> int:
    """Returns the lower limit of one of the six pre-defined dB ranges based on dB.
    """
    if db >= 70.0: return 70
    elif db >= 65.0: return 65
    elif db >= 60.0: return 60
    elif db >= 55.0: return 55
    elif db >= 50.0: return 50
    else: return 40

def __get_coord_list(geom: LineString) -> List[List[float]]:
    coords_list = geom.coords
    return [ [round(coords[0], 6), round(coords[1], 6)] for coords in coords_list]

def __get_geojson_feature_dict(coords: List[tuple], db: int) -> dict:
    """Returns a dictionary with GeoJSON schema and geometry based on the given geometry. The returned dictionary can be used as a
    feature inside a GeoJSON feature collection. 
    """
    feature = { 
        'type': 'Feature', 
        'properties': { 'db': db }, 
        'geometry': {
            'coordinates': coords,
            'type': 'LineString'
            }
        }
    return feature

def __as_geojson_feature_collection(df_dicts) -> dict:
    features = [__get_geojson_feature_dict(d['coords'], d['db']) for d in df_dicts]
    return {
        "type": "FeatureCollection",
        "features": features
    }

def create_geojson(graph: ig.Graph) -> dict:
    df = ig_utils.get_edge_gdf(graph, attrs=[E.id_way, E.length, E.noises], geom_attr=E.geom_wgs)
    # drop edges with duplicate geometry
    df = df.drop_duplicates(E.id_way.name)
    # drop edges without geometry
    df = df[df[E.geom_wgs.name].apply(lambda geom: isinstance(geom, LineString))]
    df[E.noises.name] = df.apply(lambda x: __update_db_40_exp(x[E.noises.name], x[E.length.name]), axis=1)
    df['db'] = df.apply(lambda x: __get_mean_noise_level(x[E.noises.name], x[E.length.name]), axis=1)
    df['db'] = [__get_noise_range(db) for db in df['db']]
    df['coords'] = [__get_coord_list(geom) for geom in df[E.geom_wgs.name]]
    return __as_geojson_feature_collection(df[['coords', 'db']].to_dict('records'))

def write_geojson(geojson_dict: dict, out_file: str, overwrite: bool=False) -> None:
    if overwrite and os.path.isfile(out_file):
        os.remove(out_file)
    # json_text = json.dumps(geojson_dict, indent=1)

    # begin FeatureCollection wrapper
    the_file = open(out_file, 'w')
    the_file.write('{ "type": "FeatureCollection", "features": [\n')
    the_file.close()

    write_line_delimited_geojson(geojson_dict, out_file)

    # end FeatureCollection wrapper
    the_file = open(out_file, 'a')
    the_file.write(']}')
    the_file.close()
    
def write_line_delimited_geojson(geojson_dict: dict, out_file: str, overwrite: bool=False) -> None:
    if overwrite and os.path.isfile(out_file):
        os.remove(out_file)
    separator = '\n'
    the_file = open(out_file, 'a')
    for feature in geojson_dict['features']:
        the_file.write(json.dumps(feature, separators=(',', ':')) + separator)
    the_file.close()
