import pyproj
from functools import partial
from shapely.ops import transform

def project_geom(geom, from_epsg: int = 4326, to_epsg: int = 3879):
    """Projects Shapely geometry object (e.g. Point or LineString) to another CRS. 
    The default conversion is from EPSG 4326 to 3879.
    """
    from_epsg_str = 'epsg:'+ str(from_epsg)
    to_epsg_str = 'epsg:'+ str(to_epsg)
    project = partial(
        pyproj.transform,
        pyproj.Proj(init=from_epsg_str),
        pyproj.Proj(init=to_epsg_str))
    geom_proj = transform(project, geom)
    return geom_proj
