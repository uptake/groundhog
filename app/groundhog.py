
import logging
import sys
import time
import psutil
import argparse
import json
from copy import deepcopy
import multiprocessing as mp
from flask import Flask, request, Response, jsonify
import srtm_elevation_and_slope as srtm_methods

logger = logging.getLogger()


# Flask object for resident support
flask_app = Flask(__name__)
VERSION = "0.3"
DEFAULT_STRIDE = 250.0


class Heading:
    """
    A simple class to bundle space-time coordinates
    NOTE: latitudes MUST be -180 to 180
    """
    latitude = None
    longitude = None
    bearing = None
    stride = None
    unique_key = None

    def __init__(self, latitude, longitude, bearing=None, stride=DEFAULT_STRIDE, unique_key=None):
        if longitude > 180.0:
            longitude = longitude - 360.0
        self.latitude = latitude
        self.longitude = longitude
        self.bearing = bearing
        self.stride = stride
        self.unique_key = unique_key

    def info(self):
        logger.info("lat|lon at bearing:stride (key) = " +
                    str(self.latitude) + "|" +
                    str(self.longitude) + " at " +
                    str(self.bearing) + ":" +
                    str(self.stride) + " (" +
                    str(self.unique_key) + ")")

    def to_dict(self):
        return {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "bearing": self.bearing,
                "stride": self.stride,
                "unique_key": self.unique_key
               }


def report_sys_info():
    """
    Report basic system stats
    """
    logger.info("Python version  : " + sys.version)
    logger.info("Number of CPUs  : " + str(psutil.cpu_count()))
    logger.info("Memory total    : " + str(round(float(psutil.virtual_memory().total) / 2 ** 30, 2)) + "GB")
    logger.info("Memory useage   : " + str(round(float(psutil.virtual_memory().used) / 2 ** 30, 2)) + "GB")
    logger.info("Memory available: " + str(round(float(psutil.virtual_memory().available) / 2 ** 30, 2)) + "GB")


def get_command_line():
    """
    Get command line arguments
    """
    ap = argparse.ArgumentParser(description="Terrain slope reporter v" + VERSION)
    # Switches
    ap.add_argument("-d", "--debug", dest="debug", action="store_true", help="Switch to activate debug mode.")
    ap.set_defaults(debug=False)
    ap.add_argument("-p", '--port', type=int, default=5005,
                    help='Port you wan to run this on.', required=False)
    command_line_args = ap.parse_args()
    return command_line_args


def make_health_check():
    """
    Makes a check that the network is responding for
    monitoring purposes in operations
    """
    return Response(json.dumps({"status": "OK"}), mimetype='application/json')


def help_response():
    """
    Return help documentation to guide the user
    """
    help_message = """
        <xmp>
           ___                           _ _
          / _ \_ __ ___  _   _ _ __   __| | |__   ___   __ _
         / /_\/ '__/ _ \| | | | '_ \ / _` | '_ \ / _ \ / _` |
        / /_\\\\| | | (_) | |_| | | | | (_| | | | | (_) | (_| |
        \____/|_|  \___/ \__,_|_| |_|\__,_|_| |_|\___/ \__, |
                                                       |___/

        ENDPOINTS:
        /help - to request a help doc
        /health - make health check
        /groundhog - to request terrain/slope data

        GROUNDHOG VARIABLES:
        lat - latitude of interest (-90.0 to 90.0 degrees North)
        lon - longitude of interest (-180.0 to 180.0 degrees East)
        bearing - Compass bearing for slope (cardinal degrees, 0 is North)

        or:
        coords - a list of coordinates (NOT IMPLEMENTED YET)

        optional:
        stride (optional, default=250.0) - resolution to calculate slope on in meters (larger is smoother)

        SAMPLE REST CALL:
        http://localhost:5005/groundhog?lat=45.2&lon=-101.3

        SAMPLE JSON PAYLOAD (OPTIONAL - bearing, stride, unique_key):
        [{
            'latitude': 45.0,
            'longitude': -110.0,
            'bearing': 123.45,
            'stride': 250.0,
            'unique_key': 'foo'
        }, {
            'latitude': 45.05,
            'longitude': -109.95,
            'bearing': 133.31,
            'stride': 500.0,
            'unique_key': 'bar'
        }, ...]
        </xmp>
    """
    return help_message


def make_json_response(data_list):
    """
    Takes a dictionary response and converts it to a JSON object for web return
    """
    results = []
    # Parse the list of data returns
    if data_list is not None:
        for data_dict in data_list:
            result = deepcopy(data_dict)
            lat = float(result['latitude'])
            lon = float(result['longitude'])
            result.pop('latitude', None)
            result.pop('longitude', None)
            result['geo_point'] = {'lat': lat, 'lon': lon}
            results.append(result)

    # Some versions of flask don't like jsonify
    # https://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
    return Response(json.dumps(results), mimetype='application/json')


def json_to_headings(json_coords):
    """
    Converts an uploaded csv file to a list of coordinate objects
    """
    assert isinstance(json_coords, list)
    coords = []
    for coord in json_coords:
        # lat and lon are required (get method is safe so no need for trys)
        latitude = coord.get("latitude")
        longitude = coord.get("longitude")

        # Try geo_point format
        if (latitude is None) or (longitude is None):
            geo_point = coord.get("geo_point")
            latitude = geo_point.get("lat")
            longitude = geo_point.get("lon")
            # Give up if no coord info found
            if (latitude is None) or (longitude is None):
                logger.error("Problem in latitude/longitude info in JSON.")
                raise KeyError
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            logger.error("Problem in parsing latitude/longitude given as float.")
            raise ValueError
        if coord.get("bearing") is not None:
            bearing = float(coord.get("bearing"))
        else:
            bearing = None
        if coord.get("stride") is not None:
            stride = float(coord.get("stride"))
        else:
            stride = DEFAULT_STRIDE
        unique_key = coord.get("unique_key")
        # Bearing and unique_key aren't required
        coords.append(Heading(latitude, longitude, bearing=bearing, stride=stride, unique_key=unique_key))
    return coords


def rest_to_heading(params):
    """
    Takes the REST call and turns it into a coordinate
    In the future this could get fancier
    """
    latitude = None
    longitude = None
    bearing = None
    stride = DEFAULT_STRIDE
    for key, value in params.items():
        if (key == 'latitude') or (key == 'lat'):
            latitude = float(value)
        if (key == 'longitude') or (key == 'lon'):
            longitude = float(value)
        if key == 'bearing':
            bearing = float(value)
        if key == 'stride':
            stride = float(value)
    if (latitude is None) or (longitude is None):
        logger.error("Required latitude, longitude not given.")
        return None
    return [Heading(latitude, longitude, bearing=bearing, stride=stride)]


def from_heading(heading):
    elevation, slope = srtm_methods.slope_from_coord_bearing(heading.longitude,
                                                             heading.latitude,
                                                             heading.bearing,
                                                             stride_length=heading.stride)
    return elevation, slope


def from_heading_list(heading_list):
    # TODO: this is really hamfisted
    if heading_list[0].stride is not None:
        stride_length = heading_list[0].stride
    else:
        stride_length = DEFAULT_STRIDE
    bearing_list = None  # In case we don't need it
    coord_list = []
    # If bearings are given:
    if heading_list[0].bearing is not None:
        elevation_list = []
        slope_list = []
        for heading in heading_list:
            this_elevation, this_slope = from_heading(heading)
            elevation_list.append(this_elevation)
            slope_list.append(this_slope)
    else:
        for heading in heading_list:
            coord_list.append((heading.longitude, heading.latitude))
        elevation_list, slope_list, bearing_list = srtm_methods.slope_from_coords_only(coord_list,
                                                                                       stride_length=stride_length)
    return elevation_list, slope_list, bearing_list


def groundhog_request(request):
    """
    Supports the request for a groundhog call
    params (obj) - a dictionary filled with option from REST request
    """
    logger.info("Groundhog has been summoned.")
    params = request.args
    # Get a list of coordinates from the REST call
    if request.method == 'POST':
        try:
            json_payload = request.get_json()
        except TypeError:
            logger.error("Problem in POST request.")
            return None
        logger.info("Coordinates posted as JSON...")
        headings = json_to_headings(json_payload)
    else:
        headings = rest_to_heading(params)

    # Curate coordinates from the REST call
    logger.info("Received " + str(len(headings)) + " coordinates to fetch.")

    # If it's a single heading assume you got a bearing, throw an error if not
    response_list = []
    response_part = headings[0].to_dict()
    if len(headings) == 1:
        elevation, slope = from_heading(headings[0])
        response_part["elevation"] = elevation
        response_part["slope"] = slope
        response_list.append(response_part)
        # logger.info("elevation: {}".format(elevation))
        # logger.info("slope {}".format(slope))
    # If it's a list can use one of two methods, prefer given bearings
    else:
        elevation_list, slope_list, bearing_list = from_heading_list(headings)
        for i in range(len(headings)):
            response_part = headings[i].to_dict()
            response_part["elevation"] = elevation_list[i]
            response_part["slope"] = slope_list[i]
            if response_part.get("bearing") is None:
                response_part["bearing"] = bearing_list[i]
            response_list.append(response_part)
    return response_list


# Define Flask options
# Standard health check
@flask_app.route("/health")
def health_check():
    logger.info("Received /health request from: " + request.remote_addr)
    return make_health_check()


# Give help
@flask_app.route("/")
def do_none_help():
    logger.info("Received / request from: " + request.remote_addr)
    return help_response()


@flask_app.route("/help")
def do_help_message():
    logger.info("Received /help request from: " + request.remote_addr)
    return help_response()


# Main endpoint
@flask_app.route("/groundhog", methods=['GET', 'POST'])
def groundhog():
    logger.info("Received /groundhog request from: " + request.remote_addr)
    data_list = groundhog_request(request)
    return make_json_response(data_list)


if __name__ == "__main__":
    start = time.clock()
    report_sys_info()

    args = get_command_line()  # Read command line arguments
    if args.debug:
        logger.setLevel("DEBUG")  # Set the logging level to verbose
    else:
        logger.setLevel("INFO")  # Set the logging level to normal

    pool = mp.Pool()  # Instantiate a pool object
    flask_app.config["pool"] = mp.pool.Pool()
    flask_app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB limit (this is really big)
    flask_app.run(host="0.0.0.0", port=args.port, debug=args.debug, use_reloader=False)

    # Shut down and clean up
    logger.info("Execution time: " + str(round((time.clock() - start) * 1000, 1)) + " ms")
    logger.info("All Done!")
    try:
        mp.sys.exit()
    except SystemError:
        sys.tracebacklimit = 0
        pass
