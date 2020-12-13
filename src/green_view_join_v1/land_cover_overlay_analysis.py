import sys
sys.path.append('..')
from enum import Enum
from common.logger import Logger
from db import get_sql_executor


log = Logger(printing=True, log_file=r'land_cover_overlay_analysis.log', level='debug')

execute_sql = get_sql_executor(log)


class Table(Enum):
    edge_buffers = 'edge_buffers_subset'
    low_vegetation = 'low_vegetation'
    low_vegetation_parks = 'low_vegetation_parks'
    trees_2_10m = 'trees_2_10m'
    trees_10_15m = 'trees_10_15m'
    trees_15_20m = 'trees_15_20m'
    trees_20m = 'trees_20m'


class OverlayTable(Enum):
    low_vegetation_comb = 'low_vegetation_comb'
    edge_buffers_low_vegetation_intersect = 'edge_buffers_low_vegetation_intersect'
    edge_buffers_low_vegetation_union = 'edge_buffers_low_vegetation_union'


# 1) make sure we have all the tables we need in the database
db_tables = execute_sql(
    f'''
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    ''', 
    returns=True, 
    dry_run=False
)
table_names = [r for r, in db_tables]
for table in Table:
    if table.value not in table_names:
        log.warning(f'Table {table.value} is not in the database')


# 2) combine low vegetation layers and fix invalid geometries
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.low_vegetation_comb.value};

    CREATE TABLE {OverlayTable.low_vegetation_comb.value}
    AS (
        SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.low_vegetation.value}
        UNION ALL
        SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.low_vegetation_parks.value}
    );

    ALTER TABLE {OverlayTable.low_vegetation_comb.value}
        ALTER COLUMN geom TYPE geometry(Polygon, 3879);

    CREATE INDEX low_vegetation_comb_geom_idx ON {OverlayTable.low_vegetation_comb.value}
        USING GIST (geom);
    ''', 
    dry_run=True
)


# 3) intersect low vegetation with edge buffers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_low_vegetation_intersect.value};

    CREATE TABLE {OverlayTable.edge_buffers_low_vegetation_intersect.value}
    AS (
        SELECT EDGE.id_ig, (ST_Dump(ST_Intersection(EDGE.geom, LOW_VEG.geom))).geom
        FROM {Table.edge_buffers.value} AS EDGE,
            {OverlayTable.low_vegetation_comb.value} AS LOW_VEG
        WHERE ST_Intersects(EDGE.geom, LOW_VEG.geom)
    );

    ALTER TABLE {OverlayTable.edge_buffers_low_vegetation_intersect.value}
        ALTER COLUMN geom TYPE geometry(Polygon, 3879);

    CREATE INDEX {Table.edge_buffers.value}_low_vegetation_intersect_geom_idx
        ON {OverlayTable.edge_buffers_low_vegetation_intersect.value}
        USING GIST (geom);
    ''', 
    dry_run=True
)


# 4) dissolve intersection geometries with edge id and calculate areas 
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_low_vegetation_union.value};

    CREATE TABLE {OverlayTable.edge_buffers_low_vegetation_union.value}
    AS (
        SELECT id_ig, geom, ST_Area(geom) AS area FROM (
            SELECT id_ig, ST_Multi(ST_Union(geom)) as geom
            FROM {OverlayTable.edge_buffers_low_vegetation_intersect.value}
            GROUP BY id_ig
        ) AS sub
    );

    ALTER TABLE {OverlayTable.edge_buffers_low_vegetation_union.value}
        ALTER COLUMN geom TYPE geometry(MultiPolygon, 3879);
    ''', 
    dry_run=True
)
