import sys
sys.path.append('..')
import os
import traceback
from pyproj import CRS
import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from common.logger import Logger
from noise_data.schema import Layer as L
import common.geometry as geom_utils
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

def explode_multipolygons_to_polygons(log: Logger, polygon_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    row_accumulator = []
    def explode_multipolygons(row):
        if (row['geometry'].type == 'MultiPolygon'):
            for geom in row['geometry'].geoms:
                new_row = row.to_dict()
                new_row['geometry'] = geom
                row_accumulator.append(new_row)
        else:
            row_accumulator.append(row.to_dict())

    polygon_gdf.apply(explode_multipolygons, axis=1)
    gdf = gpd.GeoDataFrame(row_accumulator, crs=CRS.from_epsg(3879))
    if (len(polygon_gdf) != len(gdf)):
        log.debug(f'Exploaded {len(gdf)} polygons from {len(polygon_gdf)} multipolygons')
    return gdf

def filter_out_features_outside_mask(log: Logger, gdf, mask_poly):
    gdf['inside'] = [True if mask_poly.intersects(geom.boundary) else False for geom in gdf['geometry']]
    filtered = gdf[gdf['inside'] == True]
    log.debug(f'Filtered out {len(gdf)-len(filtered)} rows outside the mask of total {len(gdf)} rows')
    return filtered

def get_noise_data(
    log: Logger = Logger(printing=True),
    hel_wfs_download: bool = False,
    process_hel: bool = False,
    process_espoo: bool = False,
    process_syke: bool = False,
    mask_poly_file: str = None,
    noise_layer_info_csv: str = None,
    noise_data_hel_gpkg: str = None,
    processed_data_gpkg: str = None,
    wfs_hki_url: str = None,
    ):
    
    if (None in [noise_data_hel_gpkg, processed_data_gpkg]):
        raise ValueError('Arguments noise_data_hel_gpkg and processed_data_gpkg must be specified')
    
    try:
        noise_layer_info = pd.read_csv(noise_layer_info_csv).to_dict('records')
    except Exception:
        log.error('Missing or invalid argument noise_layer_info_csv')
        log.error(traceback.format_exc())

    if os.path.exists(processed_data_gpkg):
        log.info(f'Removing previously processed data in {processed_data_gpkg}')
        try:
            os.remove(processed_data_gpkg)
        except Exception:
            log.error('Error in removing data')

    mask_poly = geom_utils.project_geom(gpd.read_file(mask_poly_file)['geometry'][0]).buffer(500)

    if (hel_wfs_download == True):
        log.info('Starting to download noise data from Helsinki (WFS)')
        log.info(f'Initializing WFS connection to {wfs_hki_url}')
        wfs_hki = WebFeatureService(url=wfs_hki_url)
        log.info(f'Initialized WFS connection with name: {wfs_hki.identification.title} and version: {wfs_hki.version}')
        log.info(f'Found available methods: {[operation.name for operation in wfs_hki.operations]}')

        for layer in noise_layer_info:
            if (layer[L.source.name] == 'hel'):
                try:
                    log.info(f'Downloading WFS layer from {wfs_hki.identification.title}: {layer["name"]}')
                    noise_features = get_wfs_feature(wfs_hki_url, layer['name'])
                    noise_features.to_file(noise_data_hel_gpkg, layer=layer['export_name'], driver='GPKG')
                    log.info(f'Exported features to file: {layer["export_name"]}')
                except Exception:
                    log.error(traceback.format_exc())

        log.info('Noise data from Helsinki downloaded (WFS)')
    else:
        log.info('Skipping noise data download from Helsinki WFS')

    log.info('Starting to process noise data')
    for layer in noise_layer_info:
        read_data = False
        if (layer[L.source.name] == 'hel' and process_hel == True):
            log.info(f'Processing layer from {layer["source"]}: {layer["name"]}')
            gdf = gpd.read_file(noise_data_hel_gpkg, layer=layer['export_name'])
            read_data = True
        if (layer[L.source.name] == 'espoo' and process_espoo == True):
            log.info(f'Processing layer from {layer["source"]}: {layer["name"]}')
            gdf = gpd.read_file(layer['name'])
            read_data = True
        if (layer[L.source.name] == 'syke' and process_syke == True):
            log.info(f'Processing layer from {layer["source"]}: {layer["name"]}')
            gdf = gpd.read_file(layer['name'])
            gdf = filter_out_features_outside_mask(log, gdf, geom_utils.project_geom(mask_poly, geom_epsg=3879, to_epsg=3047))
            gdf = gdf.to_crs(epsg=3879)
            # extract db low from strings like '55-60' and '>70'
            gdf[layer['noise_attr']] = [int(db[-2:]) if (len(db) == 3) else int(db[:2]) for db in gdf[layer['noise_attr']]]
            read_data = True
        if (read_data == True):
            gdf = explode_multipolygons_to_polygons(log, gdf)
            gdf = gdf.rename(columns={ layer['noise_attr']: L.db_low.name })
            gdf[['geometry', L.db_low.name]].to_file(processed_data_gpkg, layer=layer['export_name'], driver='GPKG')

    log.info('All data processed')

if (__name__ == '__main__'):
    get_noise_data(
        log=Logger(printing=True, log_file='noise_data_preprocessing.log', level='info'),
        hel_wfs_download = False,
        process_hel = True,
        process_espoo = True,
        process_syke = True,
        mask_poly_file = 'extent_data/HMA.geojson',
        noise_layer_info_csv = 'noise_data/noise_layers.csv',
        noise_data_hel_gpkg = 'noise_data/noise_data_raw.gpkg',
        processed_data_gpkg = 'noise_data/noise_data_processed.gpkg',
        wfs_hki_url = 'https://kartta.hel.fi/ws/geoserver/avoindata/wfs',
    )
