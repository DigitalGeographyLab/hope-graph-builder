import sys
sys.path.append('..')
from enum import Enum
from common.logger import Logger
import db


subset = True

edge_buffers_table: str = 'edge_buffers_subset' if subset else 'edge_buffers'
log = Logger(printing=True, log_file=r'land_cover_overlay_analysis.log')
execute_sql = db.get_sql_executor(log)


class Table(Enum):
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
    edge_buffers_low_vegetation_shares = 'edge_buffers_low_vegetation_shares'
    high_vegetation_comb = 'high_vegetation_comb'
    edge_buffers_high_vegetation_intersect = 'edge_buffers_high_vegetation_intersect'
    edge_buffers_high_vegetation_union = 'edge_buffers_high_vegetation_union'
    edge_buffers_high_vegetation_shares = 'edge_buffers_high_vegetation_shares'

class Column(Enum):
    low_vegetation_share = 'low_vegetation_share'
    high_vegetation_share = 'high_vegetation_share'


# 1.0 make sure we have all the tables we need in the database
table_names = db.get_db_table_names(execute_sql)
for table in Table:
    if table.value not in table_names:
        log.warning(f'Table {table.value} is not in the database')


# 2.1 combine low vegetation layers and fix invalid geometries
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

    CREATE INDEX {OverlayTable.low_vegetation_comb.value}_geom_idx ON {OverlayTable.low_vegetation_comb.value}
        USING GIST (geom);
    ''', 
    dry_run=True
)


# 2.2 intersect low vegetation with edge buffers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_low_vegetation_intersect.value};

    CREATE TABLE {OverlayTable.edge_buffers_low_vegetation_intersect.value}
    AS (
        SELECT EDGE.id_ig, (ST_Dump(ST_Intersection(EDGE.geom, LOW_VEG.geom))).geom
        FROM {edge_buffers_table} AS EDGE,
            {OverlayTable.low_vegetation_comb.value} AS LOW_VEG
        WHERE ST_Intersects(EDGE.geom, LOW_VEG.geom)
    );

    ALTER TABLE {OverlayTable.edge_buffers_low_vegetation_intersect.value}
        ALTER COLUMN geom TYPE geometry(Polygon, 3879);

    CREATE INDEX {edge_buffers_table}_low_vegetation_intersect_geom_idx
        ON {OverlayTable.edge_buffers_low_vegetation_intersect.value}
        USING GIST (geom);
    ''', 
    dry_run=True
)


# 2.3 dissolve intersection geometries with edge id and calculate areas 
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


# 2.4 calculate low vegetation shares for edge buffers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_low_vegetation_shares.value};

    CREATE TABLE {OverlayTable.edge_buffers_low_vegetation_shares.value}
    AS (
        SELECT E_VEG.id_ig, ROUND((E_VEG.area/ST_Area(E.geom))::decimal, 3) as {Column.low_vegetation_share.value}
        FROM {OverlayTable.edge_buffers_low_vegetation_union.value} as E_VEG
        JOIN {edge_buffers_table} AS E ON E.id_ig = E_VEG.id_ig);
    ''', 
    dry_run=True
)


# 3.1 combine high vegetation layers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.high_vegetation_comb.value};

    CREATE TABLE {OverlayTable.high_vegetation_comb.value}
    AS (
        SELECT geom FROM (
            SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.trees_2_10m.value}
            UNION ALL
            SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.trees_10_15m.value}
            UNION ALL
            SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.trees_15_20m.value}
            UNION ALL
            SELECT (ST_Dump(ST_MakeValid(ST_Multi(geom)))).geom FROM {Table.trees_20m.value}
        ) VEG_COMB
        WHERE ST_GeometryType(geom) = 'ST_Polygon'
    );

    ALTER TABLE {OverlayTable.high_vegetation_comb.value}
        ALTER COLUMN geom TYPE geometry(Polygon, 3879);

    CREATE INDEX {OverlayTable.high_vegetation_comb.value}_geom_idx ON {OverlayTable.high_vegetation_comb.value}
        USING GIST (geom);
    ''',
    dry_run=True
)


# 3.2 intersect high vegetation with edge buffers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_high_vegetation_intersect.value};

    CREATE TABLE {OverlayTable.edge_buffers_high_vegetation_intersect.value}
    AS (
        SELECT EDGE.id_ig, (ST_Dump(ST_Intersection(EDGE.geom, HIGH_VEG.geom))).geom
        FROM {edge_buffers_table} AS EDGE,
            {OverlayTable.high_vegetation_comb.value} AS HIGH_VEG
        WHERE ST_Intersects(EDGE.geom, HIGH_VEG.geom)
    );

    ALTER TABLE {OverlayTable.edge_buffers_high_vegetation_intersect.value}
        ALTER COLUMN geom TYPE geometry(Polygon, 3879);

    CREATE INDEX {edge_buffers_table}_high_vegetation_intersect_geom_idx
        ON {OverlayTable.edge_buffers_high_vegetation_intersect.value}
        USING GIST (geom);
    ''', 
    dry_run=True
)


# 3.3 dissolve intersection geometries with edge id and calculate areas 
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_high_vegetation_union.value};

    CREATE TABLE {OverlayTable.edge_buffers_high_vegetation_union.value}
    AS (
        SELECT id_ig, geom, ST_Area(geom) AS area FROM (
            SELECT id_ig, ST_Multi(ST_Union(geom)) as geom
            FROM {OverlayTable.edge_buffers_high_vegetation_intersect.value}
            GROUP BY id_ig
        ) AS sub
    );

    ALTER TABLE {OverlayTable.edge_buffers_high_vegetation_union.value}
        ALTER COLUMN geom TYPE geometry(MultiPolygon, 3879);
    ''', 
    dry_run=True
)


# 3.4 calculate high vegetation shares for edge buffers
execute_sql(
    f'''
    DROP TABLE IF EXISTS {OverlayTable.edge_buffers_high_vegetation_shares.value};

    CREATE TABLE {OverlayTable.edge_buffers_high_vegetation_shares.value}
    AS (
        SELECT E_VEG.id_ig, ROUND((E_VEG.area/ST_Area(E.geom))::decimal, 3) as {Column.high_vegetation_share.value}
        FROM {OverlayTable.edge_buffers_high_vegetation_union.value} as E_VEG
        JOIN {edge_buffers_table} AS E ON E.id_ig = E_VEG.id_ig);
    ''', 
    dry_run=True
)
