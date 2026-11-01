# sentinel2_extractor

Simple script to extract an area of interest from the Sentinel 2. Example:

```bash
./extract.py --lat -42.336532 --long 173.682132 --startdate 2025-10-20 --enddate 2025-10-25
``` 

Set the `AWS_NO_SIGN_REQUEST=YES` env var to avoid GDAL trying to log you
in. You don't need a log in for this data - it is part of AWS' OpenData offering.
 