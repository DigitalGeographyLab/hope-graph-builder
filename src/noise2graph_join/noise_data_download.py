import sys
sys.path.append('..')
import traceback
import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from common.logger import Logger
import pandas as pd
import geopandas as gpd

def get_wfs_feature(url: str, layer: str, version: str='1.0.0', request: str='GetFeature') -> gpd.GeoDataFrame:
    params = dict(
        service='WFS',
        version=version,
        request=request,
        typeName=layer,
        outputFormat='json'
        )
    q = Request('GET', url, params=params).prepare().url
    return gpd.read_file(q)

def get_noise_data(
    log: Logger=Logger(printing=True),
    hel_wfs_download: bool=True,
    hel_process: bool=True,
    syke_process: bool=True,
    noise_layer_info_csv: str=None,
    raw_data_gpkg: str=None,
    wfs_hki_url: str=None,
    ):
    
    if (raw_data_gpkg == None):
        raise ValueError('Argument raw_data_gpkg must be specified')
    
    try:
        noise_layer_info = pd.read_csv(noise_layer_info_csv).to_dict('records')
    except Exception:
        log.error('Missing or invalid argument noise_layer_info_csv')
        log.error(traceback.format_exc())

    if (hel_wfs_download == True):
        log.info('Starting Helsinki noise data download from WFS')
        log.info(f'Initializing WFS connection to {wfs_hki_url}')
        wfs_hki = WebFeatureService(url=wfs_hki_url)
        log.info(f'Initialized WFS connection with name: {wfs_hki.identification.title} and version: {wfs_hki.version}')
        log.info(f'Found available methods: {[operation.name for operation in wfs_hki.operations]}')

        for layer in noise_layer_info:
            if (layer['source'] == 'hel'):
                try:
                    log.info(f'Downloading WFS layer from {wfs_hki.identification.title}: {layer["name"]}')
                    noise_features = get_wfs_feature(wfs_hki_url, layer['name'])
                    noise_features.to_file(raw_data_gpkg, layer=layer['export_name'], driver='GPKG')
                    log.info(f'Exported features to file: {layer["export_name"]}')
                except Exception:
                    log.error(traceback.format_exc())

        log.info('Helsinki noise data downloaded from WFS')
    else:
        log.info('Skipping noise data download from Helsinki WFS')
        
    log.info('All data processed')

if (__name__ == '__main__'):
    get_noise_data(
        log=Logger(printing=True, log_file='get_noise_data.log', level='info'),
        hel_wfs_download=True,
        hel_process=True,
        syke_process=True,
        noise_layer_info_csv='noise_data/noise_layers.csv',
        raw_data_gpkg='noise_data/noise_data_raw.gpkg',
        wfs_hki_url='https://kartta.hel.fi/ws/geoserver/avoindata/wfs',
    )
