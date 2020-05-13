import pyproj
from pyproj import CRS
from functools import partial
from shapely.ops import transform

def project_geom(geom, geom_epsg: int = 4326, to_epsg: int = 3879):
    """Projects Shapely geometry object (e.g. Point or LineString) to another CRS. 
    The default conversion is from EPSG 4326 to 3879.
    """
    from_epsg_str = 'epsg:'+ str(geom_epsg)
    to_epsg_str = 'epsg:'+ str(to_epsg)

    project = pyproj.Transformer.from_crs(
        crs_from=CRS(from_epsg_str), 
        crs_to=CRS(to_epsg_str),
        always_xy=True)

    return transform(project.transform, geom) 
