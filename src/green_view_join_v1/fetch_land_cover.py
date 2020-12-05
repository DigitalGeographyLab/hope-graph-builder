import sys
sys.path.append('..')
from common.logger import Logger
from typing import Dict
import fiona
from geopandas import GeoDataFrame
from dataclasses import dataclass
import geopandas as gpd
from enum import Enum
from requests import Request
from functools import partial


hsy_wfs_url = 'https://kartta.hsy.fi/geoserver/wfs'


@dataclass
class VegetationLayers:
    low_vegetation: GeoDataFrame
    low_vegetation_parks: GeoDataFrame = None
    trees_2_10m: GeoDataFrame = None
    trees_10_15m: GeoDataFrame = None
    trees_15_20m: GeoDataFrame = None
    trees_20m: GeoDataFrame = None


@dataclass
class CombinedVegetationLayers:
    low_vegetation: GeoDataFrame
    high_vegetation: GeoDataFrame


class HsyWfsLayerName(Enum):
    low_vegetation = 'matala_kasvillisuus'
    low_vegetation_parks = 'maanpeite_muu_avoin_matala_kasvillisuus_2018'
    trees_2_10m = 'maanpeite_puusto_2_10m_2018'
    trees_10_15m = 'maanpeite_puusto_10_15m_2018'
    trees_15_20m = 'maanpeite_puusto_15_20m_2018'
    trees_20m = 'maanpeite_puusto_yli20m_2018'
    water = 'maanpeite_vesi_2018'


def __fetch_wfs_layer(
    url: str,
    layer: str,
    version: str = '1.0.0', 
    request: str = 'GetFeature',
) -> GeoDataFrame:
    params = dict(
        service = 'WFS',
        version = version,
        request = request,
        typeName = layer,
        outputFormat = 'json'
        )
    q = Request('GET', url, params=params).prepare().url
    return gpd.read_file(q)


def fetch_hsy_vegetation_layers(log, land_cover_cache_gpkg: str) -> VegetationLayers:

    fetch_wfs_layer = partial(__fetch_wfs_layer, hsy_wfs_url)
    fetched_layers = fiona.listlayers(land_cover_cache_gpkg)

    layers: Dict[HsyWfsLayerName, GeoDataFrame] = {}

    for idx, layer_name in enumerate(HsyWfsLayerName):

        if idx > 0:
            break

        if layer_name.name in fetched_layers:
            log.info(f'Loading layer {idx+1}/{len(HsyWfsLayerName)}: {layer_name.name} from cache')
            gdf = gpd.read_file(land_cover_cache_gpkg, layer=layer_name.name)
            layers[layer_name.name] = gdf
        else:
            log.info(f'Fetching WFS layer {idx+1}/{len(HsyWfsLayerName)}: {layer_name.name} from "{layer_name.value}"')
            gdf = fetch_wfs_layer(layer_name.value)
            gdf.to_file(land_cover_cache_gpkg, layer=layer_name.name, driver='GPKG')
            layers[layer_name.name] = gdf

    log.info('Loaded all land cover layers')
    return VegetationLayers(**layers)


def dissolve_layer(log, gdf_in: GeoDataFrame) -> GeoDataFrame:
    log.info('Dissolving layer')
    gdf = gdf_in[['geometry']].copy()
    gdf['group'] = 1
    s_index = gdf.sindex
    gdf = gdf.dissolve(by='group')
    return gdf[['geometry']]


def combine_vegetation_layers(
    log,
    layer_cache: str,
    veg_layers: VegetationLayers
) -> CombinedVegetationLayers:
    log.info(f'Features before dissolve: {len(veg_layers.low_vegetation)}')
    veg_layers.low_vegetation = dissolve_layer(log, veg_layers.low_vegetation)
    log.info(f'Features after dissolve: {len(veg_layers.low_vegetation)}')


def get_vegetation_layers(
    log: Logger, 
    layer_cache: str
) -> CombinedVegetationLayers:

    raise NotImplementedError


if __name__ == '__main__':
    log = Logger(printing=True, log_file=r'fetch_land_cover.log', level='debug')
    land_cover_wfs_cache_gpkg = r'data/land_cover_wfs_cache.gpkg'
    vegetation_layers_gpkg = r'data/vegetation_layers.gpkg'

    # load land cover from WFS
    vegetation_layers = fetch_hsy_vegetation_layers(log, land_cover_wfs_cache_gpkg)
    combined_vege_layers = combine_vegetation_layers(log, vegetation_layers_gpkg, vegetation_layers)
