import sys
sys.path.append('..')
import traceback
import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from common.logger import Logger
import pandas as pd
import geopandas as gpd

log = Logger(printing=True)
layer_list = pd.read_csv('noise_data/noise_layers.csv')
raw_data_gpkg = 'noise_data/noise_data_raw.gpkg'
wfs_hki_url = 'https://kartta.hel.fi/ws/geoserver/avoindata/wfs'

log.info(f'Initializing WFS connection to {wfs_hki_url}')
wfs_hki = WebFeatureService(url=wfs_hki_url)

log.info(f'Initialized WFS connection with name: {wfs_hki.identification.title} and version: {wfs_hki.version}')
log.info(f'Found available methods: {[operation.name for operation in wfs_hki.operations]}')

def get_wfs_feature(url, layer) -> gpd.GeoDataFrame:
    params = dict(
        service='WFS', 
        version="1.0.0", 
        request='GetFeature',
        typeName=layer, 
        outputFormat='json'
        )
    q = Request('GET', url, params=params).prepare().url
    return gpd.read_file(q)

noise_layers = layer_list.to_dict('records')
for layer in noise_layers:
    if (layer['source'] == 'hel'):
        try:
            log.info(f'Downloading WFS layer from {wfs_hki.identification.title}: {layer["name"]}')
            noise_features = get_wfs_feature(wfs_hki_url, layer['name'])
            noise_features.to_file(raw_data_gpkg, layer=layer['export_name'], driver='GPKG')
            log.info(f'Exported features to file: {layer["export_name"]}')
        except Exception:
            log.error(traceback.format_exc())

log.info('All done')
