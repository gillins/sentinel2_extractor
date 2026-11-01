#!/usr/bin/env python3

import os
import argparse
from pystac_client import Client
from osgeo import gdal, osr

gdal.UseExceptions()

ALL_BANDS = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 
    'B07', 'B08', 'B8A', 'B11', 'B12', 'SCL']
    
    
def get_cmd_args():
    """
    Get the command line args
    """
    p = argparse.ArgumentParser()
    p.add_argument("--lat", required=True, type=float,
        help="The latitude to search")
    p.add_argument("--long", required=True, type=float,
        help="The longitude to search")
    p.add_argument("--size", default=20000, type=int,
        help="The size of the chip to extract from each image in metres (default=%(default)s)")
    p.add_argument("--epsg", default=2193, type=int,
        help="The epsg code to reproject the data into (default=%(default)s)")
    p.add_argument("--startdate", required=True,
        help="start date to search in (yyyy-mm-dd) format")
    p.add_argument("--enddate", required=True,
        help="end date to search in (yyyy-mm-dd) format")
    p.add_argument("--res", default=10, type=float,
        help="resolution to use in metres (default=%(default)s)")
        
    cmdargs = p.parse_args()
    return cmdargs


def create_image(item, res, longt, lat, epsg, wsize):
    s2_name_parts = str(item.id).split("_")
    
    year = s2_name_parts[2][:4]
    month = int(s2_name_parts[2][4:6].lstrip("0"))
    tiles = s2_name_parts[1]
    
    # Find the files in the S3 bucket
    prefix = ('/vsis3/sentinel-cogs/sentinel-s2-l2a-cogs/' +
        f'{tiles[0:2]}/{tiles[2]}/{tiles[3:5]}/{year}/{month}/{item.id}/')
    band_list = [prefix + band + '.tif' for band in ALL_BANDS]
    
    # Create a vrt file from the stack of bands
    vrt_options = gdal.BuildVRTOptions(separate=True, 
        xRes=res, yRes=res, 
        targetAlignedPixels=True, 
        resampleAlg='cubic', 
        addAlpha=False)
    vrt_name = f'{item.id}.vrt'
    if not os.path.exists(vrt_name):
        vrt = gdal.BuildVRT(vrt_name, band_list, options=vrt_options)
        vrt.FlushCache()
        vrt = None
    
    # now warp to the desired projections
    # work out the centre in the new projection
    sr1 = osr.SpatialReference()
    sr1.ImportFromEPSG(4326)
    sr1.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    sr2 = osr.SpatialReference()
    sr2.ImportFromEPSG(epsg)
    sr2.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    
    ct = osr.CoordinateTransformation(sr1, sr2)
    centre_x, centre_y, _ = ct.TransformPoint(longt, lat)
    
    # work out the window size this would mean
    wsize_2 = wsize / 2
    
    tlx = centre_x - wsize_2
    tly = centre_y + wsize_2
    brx = centre_x + wsize_2
    bry = centre_y - wsize_2
    
    warp_options = gdal.WarpOptions(outputBounds=[tlx, bry, brx, tly],
        xRes=res, yRes=res, 
        targetAlignedPixels=True,
        dstSRS=f"EPSG:{epsg}",
        format="GTiff", 
        creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=1", "ZLEVEL=1", "BIGTIFF=YES", "TILED=YES", "INTERLEAVE=BAND", "NUM_THREADS=ALL_CPUS", "BLOCKXSIZE=512", "BLOCKYSIZE=512"])
    tif_name = f'{item.id}.tif'
    if not os.path.exists(tif_name):
        tif = gdal.Warp(tif_name, vrt_name, options=warp_options)
        # write band names into descriptions
        for idx, name in enumerate(ALL_BANDS):
            band = tif.GetRasterBand(idx + 1)
            band.SetDescription(name)
    

def main():
    cmdargs = get_cmd_args()
    
    client = Client.open("https://earth-search.aws.element84.com/v1")
    client.add_conforms_to('ITEM_SEARCH')
    
    geom = {
            "type": "Point",
            "coordinates": [cmdargs.long, cmdargs.lat] # [longitude, latitude]
    }
    daterange = f'{cmdargs.startdate}/{cmdargs.enddate}'
    s2Search = client.search(
            collections=['sentinel-2-l2a'],
            datetime=daterange,
            intersects=geom)
    
    tiles = s2Search.item_collection()
    for item in tiles:
        print(item.id, item.datetime)
        create_image(item, cmdargs.res, cmdargs.long, cmdargs.lat, 
            cmdargs.epsg, cmdargs.size)
    
if __name__ == '__main__':
    main()
