from typing import Callable, Union
import env
from geopandas import GeoDataFrame
from sqlalchemy import create_engine, inspect, text
from functools import partial


def get_conn_string(db: str) -> str:
    return f'postgres://{env.db_user}:{env.db_pass}@{env.db_host}:{env.db_port}/{db}'


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

    # set geometry column name to geom
    with sql_engine.connect() as conn:
        result = conn.execute(
            f'''
            ALTER TABLE {table_name} RENAME COLUMN geometry TO geom;
            ALTER INDEX idx_{table_name}_geometry
                RENAME TO idx_{table_name}_geom;
            '''
        )


def get_db_writer(
    log,
    b_inspect: bool = False, 
    inspect_table: str = None, 
    db: str = 'gp'
) -> Callable[[GeoDataFrame, str, str, bool], None]:

    engine = create_engine(get_conn_string(db))  
    
    if b_inspect and inspect_table:
        inspector = inspect(engine)
        print(inspector.get_columns(inspect_table))
    
    return partial(write_to_postgis, log, engine)


def __execute_sql(
    log, 
    engine, 
    query: str, 
    logging: bool = False, 
    returns: bool = False,
    dry_run: bool = False
) -> Union[None, list]:

    log.info(f'{"Executing SQL:" if not dry_run else "Skipping SQL:"} {query}')
    sql_query = text(query.strip())

    if dry_run: return

    with engine.connect() as conn:
        result = conn.execute(sql_query)
        log.info('SQL execution finished')
        if logging or returns:
            rows = result.fetchall()
            if logging:
                for row in rows:
                    log.info(f'{row}')
            if returns:
                return rows


def get_sql_executor(
    log, 
    db: str = 'gp'
) -> Callable[
    [str, Union[bool, None], Union[bool, None], Union[bool, None]], 
    Union[list, None]
    ]:

    engine = create_engine(get_conn_string(db))
    return partial(__execute_sql, log, engine)
