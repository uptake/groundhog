""""
This module contains functions that calculate terrain elevation above sea level
and the slope associated with a moving asset

@author : Brad Beechler (brad.beechler@uptake.com)
Modified: 20171120 (Brad Beechler)
"""

import logging
import time
import argparse
from math import asin, sin, cos, pi, sqrt, atan2, degrees, radians
from numpy import power
import srtm  # weird pip install: `pip install srtm.py`

srtm_client = srtm.get_data()  # if OOM issues, set to True

logger = logging.getLogger()  # make the logs global


def get_command_line():
    """
    Get command line arguments
    """
    ap = argparse.ArgumentParser(description="Don't run this")
    # Switches
    ap.add_argument("-d", "--debug", dest="debug", action="store_true", help="Switch to activate debug mode.")
    ap.set_defaults(debug=False)
    ap.add_argument("-lat", "--latitude", type=float, help="The desired latitude (degrees north)", required=True)
    ap.add_argument("-lon", "--longitude", type=float, help="The desired longitude (degrees east)", required=True)
    ap.add_argument("-b", "--bearing", type=float, help="The compass bearing", required=True)
    ap.add_argument("-s", "--stride", type=float, help="The stride length", default=None, required=False)
    command_line_args = ap.parse_args()
    return command_line_args


def calc_earth_radius(latitude):
    """
    Returns the radius of the Earth at a specific latitude in meters using the formula:
    Rt= SQRT((((a^2cos(t))^2)+((b^2sin(t))^2))/(((acos(t))^2)+((b(sin(t))^2)))
    where a is the semi-major axis and b is the semi-minor axis
    Parameters:
        - latitude: (array of) The latitude your want
    Returns:
        - radius: (array of) Radius in kilometers
    """
    a = 6378137  # a in above formula (radius at Equator in m)
    b = 6356752  # b in above formula (radius at Pole in m)

    # Convert latitude into radians
    latitude = radians(latitude)
    # Need to use numpy's power if the array is involved
    radius = (((power(power(a, 2) * cos(latitude), 2)) + (power(power(b, 2) * sin(latitude), 2))) /
              (power(a * cos(latitude), 2) + power(b * sin(latitude), 2)))
    radius = sqrt(radius)

    return radius


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    returns the distance in meters
    NOTE: this is approximate and could be off by as much as ~0.2%
          (this is like being off by ~1km from chicago to new york)
    """
    radius1 = calc_earth_radius(lat1)
    radius2 = calc_earth_radius(lat2)
    radius = (radius1 + radius2) / 2
    # convert decimal degrees to radians
    lat1, lat2, lon1, lon2 = map(radians, [lat1, lat2, lon1, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    # haversine formula
    a = power(sin(dlat/2), 2) + cos(lat1) * cos(lat2) * power(sin(dlon/2), 2)
    distance = 2 * asin(sqrt(a)) * radius

    return distance


def lon_lat_from_distance_bearing(lon, lat, distance, bearing):
    """
    Returns new coordinate given origin, bearing, and distance traveled
    :param lon: (float) longitude
    :param lat: (float) latitude
    :param distance: (float) distance in meters
    :param bearing: (float) compass bearing (north is 0)
    :return:
    """
    # Convert to radians
    lat_orig = radians(lat)
    lon_orig = radians(lon)
    bearing_orig = radians(bearing)
    roe = calc_earth_radius(lat_orig)
    # Calculate new coordinates
    lat_new = asin((sin(lat_orig) * cos(distance / roe)) +
                   (cos(lat_orig) * sin(distance/roe) * cos(bearing_orig)))
    lon_new = lon_orig + atan2(sin(bearing_orig) * sin(distance / roe) * cos(lat_orig),
                               cos(distance / roe) - sin(lat_orig) * sin(lat_new))
    lat_new = degrees(lat_new)
    lon_new = degrees(lon_new)

    return lon_new, lat_new


def bearing_to_components(bearing):
    """
    :param bearing: (float) compass bearing (north is 0)
    :return: vector components of bearing
    """
    rad = pi / 180.0
    x = sin(rad * bearing)
    y = cos(rad * bearing)
    return x, y


def bearing(lon1, lat1, lon2, lat2):
    """
    In general, your current heading will vary as you follow a great circle
    path, the final heading will differ from the initial heading by varying
    degrees according to distance and latitude.
    This function is for the initial bearing (sometimes referred to as forward
    azimuth)
    :param lon1: (float) longitude in degrees East of start point
    :param lat1: (float) latitude in degrees North of start point
    :param lon2: (float) longitude in degrees East of end point
    :param lat2: (float) latitude in degrees North of end point
    :return: (float) azimuth degrees (compass heading)
    """
    # Convert to radians
    lat1, lat2, lon1, lon2 = map(radians, [lat1, lat2, lon1, lon2])
    # Calculate azimuth or bearing
    delta_lon = lon2 - lon1
    x = cos(lat2) * sin(delta_lon)
    y = (cos(lat1) * sin(lat2)) - (sin(lat1) * cos(lat2) * cos(delta_lon))
    bearing = atan2(x, y)
    # Convert to degrees
    bearing = bearing * 180.0 / pi
    # Make always positive
    if bearing < 0:
        bearing = bearing + 360.0
    return bearing


def get_spiral(iterations=100):
    """
    :param iterations: (int) number of interations of spiral you want back
    :return: a list of length iterations of tuples describing a spiral on a uniform grid
    """
    spiral_list = []
    x = 0
    y = 0
    dx = 0
    dy = -1
    for _ in range(iterations):
        if ((-iterations/2 < x <= iterations/2) and
                (-iterations/2 < y <= iterations/2)):
            spiral_list.append((x, y))
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
            dx, dy = -dy, dx
        x, y = x+dx, y+dy
    return spiral_list


def get_elevation_safe(lon, lat, null_search_size=0.00028, null_search_giveup=1000):
    """
    Gets an elevation from SRTM, if it returns null do a spiral search out
    :param lon: (float) longitude
    :param lat: (float) latitude
    :param null_search_size: (float) scale to search on
    :param null_search_giveup: (int) give up after this many iterations
    :return:
    """
    elevation = srtm_client.get_elevation(lat, lon)
    if elevation is None:
        spiral = get_spiral(iterations=null_search_giveup)
        for search_factor in [1, 10, 50, 100, 200, 500]:
            # Spiral search out
            search_list = []
            for spiral_point in spiral:
                search_list.append((lon + (spiral_point[0] * (null_search_size * search_factor)),
                                    lat + (spiral_point[1] * (null_search_size * search_factor))))
            for search_point in search_list:
                elevation = srtm_client.get_elevation(search_point[1], search_point[0])
                if elevation is not None:
                    elevation = elevation
                    break
            if elevation is not None:
                break
    return elevation


def slope_from_coord_bearing(longitude_origin, latitude_origin, bearing_origin, stride_length=250.0):
    """
    Returns starting elevation and terrain slope from origin coordinate and bearing
    :param longitude_origin: (float) longitude
    :param latitude_origin: (float) latitude
    :param bearing_origin: (float) compass bearing (north is 0)
    :param stride_length: resolution you want to calculate slope on in meters (larger is smoother)
    :return: terrain elevation (meters) / meter, terrain slope (meters/meter)
    """
    elevation_origin = srtm_client.get_elevation(latitude_origin, longitude_origin)
    logger.debug("Elevation at origin: " + str(elevation_origin))

    # Bearing is an optional param
    if bearing_origin is None:
        logger.warn("No bearing given. Returning only elevation")
        return elevation_origin, None

    longitude_ahead, latitude_ahead = lon_lat_from_distance_bearing(longitude_origin, latitude_origin,
                                                                    stride_length, bearing_origin)
    longitude_behind, latitude_behind = lon_lat_from_distance_bearing(longitude_origin, latitude_origin,
                                                                      (-1.0 * stride_length), bearing_origin)

    elevation_ahead = get_elevation_safe(longitude_ahead, latitude_ahead)
    logger.debug("Elevation at coordinate ahead: " + str(elevation_ahead))
    elevation_behind = get_elevation_safe(longitude_behind, latitude_behind)
    logger.debug("Elevation at coordinate behind: " + str(elevation_behind))

    if ((elevation_origin is None) or
       (elevation_ahead is None) or
       (elevation_behind is None)):
        return None, None
    else:
        # Calculate terrain slope
        delta_elevation = elevation_ahead - elevation_behind
        logger.debug("Change in elevation = " + str(delta_elevation))
        terrain_slope = delta_elevation / stride_length
        logger.debug("Terrain slope = " + str(terrain_slope) + " m/m")
        return elevation_origin, terrain_slope


def slope_from_coords_only(coord_list, stride_length=250.0):
    """
    Returns list of terrain slopes from a list of coordinates
    :param coord_list: (list[(lon, lat)]) list of tuple coordinates as (lon,lat)
    :param stride_length: resolution you want to calculate slope on in meters (larger is smoother)
    :return:
    """
    # TODO: put time and space thresholds for sane returns
    elevation_list = []
    slope_list = []
    bearing_list = []
    for i, coord in enumerate(coord_list[:-1]):
        next_coord = coord_list[i+1]
        this_bearing = bearing(coord[0], coord[1], next_coord[0], next_coord[1])

        this_elevation, this_slope = slope_from_coord_bearing(coord[0], coord[1], this_bearing,
                                                              stride_length=stride_length)
        elevation_list.append(this_elevation)
        slope_list.append(this_slope)
        bearing_list.append(this_bearing)

    elevation_list.append(get_elevation_safe(coord_list[-1][0], coord_list[-1][1]))
    slope_list.append(None)
    bearing_list.append(None)
    return elevation_list, slope_list, bearing_list


def should_be_a_test(args):
    """
    Main code block
    """
    latitude_origin = float(args.latitude)
    longitude_origin = float(args.longitude)
    bearing_origin = float(args.bearing)

    # Check stride setting and report if using default
    if args.stride is not None:
        stride_length = float(args.stride)

    test_elev_bearing, test_slope_bearing = slope_from_coord_bearing(longitude_origin, latitude_origin, bearing_origin,
                                                                     stride_length=stride_length)
    logger.info("Terrain slope = " + str(test_slope_bearing) + " m/m")

    # TEST
    test_coords = [(-78.3, 38.32), (-78.5, 38.32), (-78.7, 38.32), (-78.8, 38.32), (-79.0, 38.32),
                   (-79.15, 38.32), (-79.3, 38.32), (-79.44, 38.32), (-79.8, 38.32), (-80.0, 38.32)]
    test_elevs, test_slopes = slope_from_coords_only(test_coords, stride_length=250.0)
    print(test_elevs)


#########################
#         DRIVER        #
#########################
if __name__ == '__main__':
    """
    Main driver if run off command line.
    """
    start = time.clock()
    args = get_command_line()  # Read command line arguments
    if args.debug:
        logger.setLevel("DEBUG")  # Set the logging level to verbose
    else:
        logger.setLevel("INFO")  # Set the logging level to normal

    logger.warning("You should really be running the groundhog.py service, this is going into tests.")
    should_be_a_test(args)

    # Shut down and clean up
    logger.info("Execution time: " + str(round((time.clock() - start) * 1000, 1)) + " ms")
    logger.info("All Done!")
