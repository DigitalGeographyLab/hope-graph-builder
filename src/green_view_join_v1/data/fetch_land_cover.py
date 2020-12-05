from geopandas import GeoDataFrame
from dataclasses import dataclass
import geopandas as gpd
from enum import Enum
from requests import Request
from functools import partial


hsy_wfs = 'https://kartta.hsy.fi/geoserver/wfs'


@dataclass
class VegetationLayers:
    low_vegetation: GeoDataFrame
    low_vegetation_parks: GeoDataFrame
    trees_2_10m: GeoDataFrame
    trees_10_15m: GeoDataFrame
    trees_15_20m: GeoDataFrame
    trees_20m: GeoDataFrame


class HsyWfsLayerName(Enum):
    low_vegetation = 'matala_kasvillisuus'
    low_vegetation_parks = 'maanpeite_muu_avoin_matala_kasvillisuus_2018'
    trees_2_10m = 'maanpeite_puusto_2_10m_2018'
    trees_10_15m = 'maanpeite_puusto_10_15m_2018'
    trees_15_20m = 'maanpeite_puusto_15_20m_2018'
    trees_20m = 'maanpeite_puusto_yli20m_2018'
    water = 'maanpeite_vesi_2018'


def __fetch_wfs_feature(
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


def fetch_hsy_vegetation_layers(log, land_cover_cache_gpkg: str):
    fetch_wfs_feature = partial(__fetch_wfs_feature, hsy_wfs)

    for idx, layer_name in enumerate(HsyWfsLayerName):
        log.info(f'Fetching WFS layer {idx+1}/{len(HsyWfsLayerName)}: {layer_name.name} from {layer_name.value}')

        land_cover = fetch_wfs_feature(layer_name.value)
        land_cover.to_file(land_cover_cache_gpkg, layer=layer_name.name, driver='GPKG')

    log.info('All WFS layers fetched')
