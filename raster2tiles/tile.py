# -*- coding: utf-8 -*-

import math
from collections import namedtuple
import gdal
import osr
import numpy as np


BoundingBox = namedtuple('BoundingBox', ['minx', 'maxx', 'miny', 'maxy'])

MAX_ZOOM_LEVEL = 32


def open_raster(raster_filepath):
    return gdal.Open(raster_filepath, gdal.GA_ReadOnly)


def _check_raster_format(raster):
    if raster.RasterCount not in (1, 3, 4):
        return False
    # TODO: check if raster dtype is uint8
    return True


def _check_out_geotransform(geo_transform):
    return (geo_transform[2], geo_transform[4]) == (0, 0)


def _get_raster_srs(raster):
    srs_wkt = raster.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(srs_wkt)
    return srs


def _get_srs_from_epsg_code(code):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(code)
    return srs


def _resolution(zoom, tile_size=256):
    initial_resolution = 2 * math.pi * 6378137 / tile_size
    res = initial_resolution / (2 ** zoom)
    return res


def _meters2pixel(x, y, zoom, tile_size=256):
    origin_shift = 2 * math.pi * 6378137 / 2.0
    res = _resolution(zoom, tile_size=tile_size)
    px = (x + origin_shift) / res
    py = (y + origin_shift) / res
    return px, py


def _pixels2meters(px, py, zoom, tile_size=256):
    origin_shift = 2 * math.pi * 6378137 / 2.0
    res = _resolution(zoom, tile_size=tile_size)
    mx = px * res - origin_shift
    my = py * res - origin_shift
    return mx, my


def _pixels2tile(px, py, tile_size=256):
    tx = int(math.ceil(px / float(tile_size)) - 1)
    ty = int(math.ceil(py / float(tile_size)) - 1)
    return tx, ty


def _meters2tile(x, y, zoom, tile_size=256):
    px, py = _meters2pixel(x, y, zoom, tile_size=tile_size)
    return _pixels2tile(px, py, tile_size=tile_size)


def _zoom_for_pixel_size(pixel_size):
    for zoom in range(MAX_ZOOM_LEVEL):
        if pixel_size > _resolution(zoom):
            return zoom - 1
    return 0


def _tile_bounds(zoom, tx, ty, tile_size=256):
    minx, miny = _pixels2meters(tx * tile_size, ty * tile_size, zoom)
    maxx, maxy = _pixels2meters((tx + 1) * tile_size, (ty + 1) * tile_size, zoom)
    # TODO: retorna uma instância de BoundingBox
    return (minx, miny, maxx, maxy)


def geo_query(ds, ulx, uly, lrx, lry, querysize=0):
    """
    For given dataset and query in cartographic coordinates returns parameters for ReadRaster()
    in raster coordinates and x/y shifts (for border tiles). If the querysize is not given, the
    extent is returned in the native resolution of dataset ds.

    raises Gdal2TilesError if the dataset does not contain anything inside this geo_query
    """
    geotran = ds.GetGeoTransform()
    rx = int((ulx - geotran[0]) / geotran[1] + 0.001)
    ry = int((uly - geotran[3]) / geotran[5] + 0.001)
    rxsize = int((lrx - ulx) / geotran[1] + 0.5)
    rysize = int((lry - uly) / geotran[5] + 0.5)

    if not querysize:
        wxsize, wysize = rxsize, rysize
    else:
        wxsize, wysize = querysize, querysize

    # Coordinates should not go out of the bounds of the raster
    wx = 0
    if rx < 0:
        rxshift = abs(rx)
        wx = int(wxsize * (float(rxshift) / rxsize))
        wxsize = wxsize - wx
        rxsize = rxsize - int(rxsize * (float(rxshift) / rxsize))
        rx = 0
    if rx+rxsize > ds.RasterXSize:
        wxsize = int(wxsize * (float(ds.RasterXSize - rx) / rxsize))
        rxsize = ds.RasterXSize - rx

    wy = 0
    if ry < 0:
        ryshift = abs(ry)
        wy = int(wysize * (float(ryshift) / rysize))
        wysize = wysize - wy
        rysize = rysize - int(rysize * (float(ryshift) / rysize))
        ry = 0
    if ry+rysize > ds.RasterYSize:
        wysize = int(wysize * (float(ds.RasterYSize - ry) / rysize))
        rysize = ds.RasterYSize - ry

    return (rx, ry, rxsize, rysize), (wx, wy, wxsize, wysize)


def _generate_tile(ds, zoom, bounds, tile_size=256):
    alpha_band = ds.GetRasterBand(1).GetMaskBand()

    raster_count = ds.RasterCount
    if alpha_band.GetMaskFlags() & gdal.GMF_ALPHA or ds.RasterCount in (4, 2):
        raster_count -= 1

    mem_driver = gdal.GetDriverByName('MEM')
    band_list = list(range(1, raster_count + 1))
    for ty in range(int(bounds.maxy), int(bounds.miny - 1), -1):
        for tx in range(int(bounds.minx), int(bounds.maxx + 1)):
            tile_bounds = _tile_bounds(zoom, tx, ty)
            querysize = tile_size * 4
            rb, wb = geo_query(ds, tile_bounds[0], tile_bounds[3], tile_bounds[2], tile_bounds[1], querysize=querysize)
            rx, ry, rxsize, rysize = rb
            wx, wy, wxsize, wysize = wb

            query_data = ds.ReadRaster(rx, ry, rxsize, rysize, wxsize, wysize, band_list=band_list)
            alpha_data = alpha_band.ReadRaster(rx, ry, rxsize, rysize, wxsize, wysize)

            window_raster = mem_driver.Create('', querysize, querysize, raster_count + 1)
            window_raster.WriteRaster(wx, wy, wxsize, wysize, query_data, band_list=band_list)
            window_raster.WriteRaster(wx, wy, wxsize, wysize, alpha_data, band_list=[raster_count + 1])

            tile_raster = mem_driver.Create('', tile_size, tile_size, window_raster.RasterCount)
            for b in range(1, tile_raster.RasterCount + 1):
                gdal.RegenerateOverview(window_raster.GetRasterBand(b), tile_raster.GetRasterBand(b), 'average')

            data = np.empty((tile_size, tile_size, tile_raster.RasterCount), dtype=np.uint8)
            for b in range(1, tile_raster.RasterCount + 1):
                data[:, :, b - 1] = tile_raster.GetRasterBand(b).ReadAsArray()

            yield (ty, tx), data


def raster2tiles(input_raster, min_zoom=None, max_zoom=None):
    if not _check_raster_format(input_raster):
        raise RuntimeError('Invalid raster format. Only rasters with 1, 3 or 4 bands are alowed!')

    input_srs = _get_raster_srs(input_raster)
    out_srs = _get_srs_from_epsg_code(3857)     # mercator

    # TODO: out_raster ta sendo usado pra algo?
    if input_srs.ExportToProj4() != out_srs.ExportToProj4():
        out_raster = gdal.AutoCreateWarpedVRT(input_raster, input_srs.ExportToWkt(), out_srs.ExportToWkt())
    else:
        out_raster = input_raster

    out_geotransform = out_raster.GetGeoTransform()
    if not _check_out_geotransform(out_geotransform):
        raise RuntimeError('Georeference of the raster contains rotation or skew.')

    # minx, maxx, miny, maxy
    out_bounds = BoundingBox(
        out_geotransform[0],
        out_geotransform[0] + out_raster.RasterXSize * out_geotransform[1],
        out_geotransform[3] - out_raster.RasterYSize * out_geotransform[1],
        out_geotransform[3])

    tile_size = 256

    # get minimal zoom level (out_geotranform[1] == raster pixel width)
    max_raster = max(out_raster.RasterXSize, out_raster.RasterYSize)
    min_zoom_level = min_zoom or _zoom_for_pixel_size(out_geotransform[1] * max_raster / float(tile_size))
    max_zoom_level = max_zoom or _zoom_for_pixel_size(out_geotransform[1])

    tiles_min_max_coordinates = {}
    for zoom in range(min_zoom_level, max_zoom_level + 1):
        tminx, tminy = _meters2tile(out_bounds.minx, out_bounds.miny, zoom, tile_size=256)
        tmaxx, tmaxy = _meters2tile(out_bounds.maxx, out_bounds.maxy, zoom, tile_size=256)
        # crop tiles extending world limits (+-180,+-90)
        tminx, tminy = max(0, tminx), max(0, tminy)
        tmaxx, tmaxy = min(2 ** zoom - 1, tmaxx), min(2 ** zoom - 1, tmaxy)
        tiles_min_max_coordinates[zoom] = BoundingBox(tminx, tmaxx, tminy, tmaxy)

    for zoom in range(min_zoom_level, max_zoom_level + 1):      # TODO: colocar isso no for de cima
        for (ty, tx), data in _generate_tile(out_raster, zoom, tiles_min_max_coordinates[zoom], tile_size=256):
            yield (zoom, ty, tx), data
