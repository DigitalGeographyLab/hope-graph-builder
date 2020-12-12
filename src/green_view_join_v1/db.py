from typing import Callable
import env
from geopandas import GeoDataFrame
from sqlalchemy import create_engine, inspect
from functools import partial


def write_to_postgis(
    log,
    sql_engine, 
    gdf: GeoDataFrame,
    table_name: str,
    if_exists: str = 'replace',
    index: bool = False
) -> None:

    log.info('Writing GeoDataFrame to PostGIS:')
    log.info(f'{gdf.head()}')

    gdf.to_postgis(
        table_name, 
        sql_engine, 
        if_exists = if_exists, 
        index = index
    )


def get_db_writer(
    log,
    b_inspect: bool = False, 
    inspect_table: str = None, 
    db: str = 'gp'
) -> Callable[[GeoDataFrame, str, str, bool], None]:

    conn_string = f'postgres://{env.db_user}:{env.db_pass}@{env.db_host}:{env.db_port}/{db}'
    engine = create_engine(conn_string)  
    
    if b_inspect and inspect_table:
        inspector = inspect(engine)
        print(inspector.get_columns(inspect_table))
    
    return partial(write_to_postgis, log, engine)
