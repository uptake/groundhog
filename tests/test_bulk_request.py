""""
This tests a bulk JSON request
"""

from uplog import log  # Make the logs global
import requests

INTERP_URL = 'http://localhost:5005/groundhog'
DEFAULT_STRIDE = 250.0


def request_with_json(json_payload):
    """
    Load interpolations from the interp service into the DB
    """
    test_response = requests.post(INTERP_URL, json=json_payload)
    test_response_json = test_response.json()
    return test_response_json


def make_test_json(size=10, stride=DEFAULT_STRIDE, use_bearing=True, use_geo_point=False):
    json_payload = []
    latitude_start = 41.52268
    longitude_start = -89.160005
    delta_latitude = 0.05
    delta_longitude = 0.05
    if use_bearing:
        test_bearing = 90.0 #233.45
    else:
        test_bearing = None

    for i in range(size):
        if use_geo_point:
            this_coord = {
                "geo_point": {"lat": latitude_start + (i * delta_latitude),
                              "lon": longitude_start + (i * delta_longitude)},
                "bearing": test_bearing,
                "stride": stride,
                "unique_key": "testing"
            }
        else:
            this_coord = {
                "latitude": latitude_start + (i * delta_latitude),
                "longitude": longitude_start + (i * delta_longitude),
                "bearing": test_bearing,
                "stride": stride,
                "unique_key": "testing"
            }

        json_payload.append(this_coord)
    return json_payload


if __name__ == '__main__':
    log.out.setLevel('INFO')  # Set the logging level to verbose
    log.out.info("Testing groundhog JSON post")

    test_json = make_test_json(size=25)
    log.out.info("Test payload (with bearings given):")
    log.out.info(test_json)
    test_response = request_with_json(test_json)
    log.out.info("Test response (with bearings given):")
    log.out.info(test_response)

    test_json = make_test_json(size=25, use_bearing=False)
    log.out.info("Test payload (without bearings given):")
    log.out.info(test_json)
    test_response = request_with_json(test_json)
    log.out.info("Test response (without bearings given):")
    log.out.info(test_response)

    test_json = make_test_json(size=25, use_geo_point=True)
    log.out.info("Test payload (with geo_points given):")
    log.out.info(test_json)
    test_response = request_with_json(test_json)
    log.out.info("Test response (with geo_points given):")
    log.out.info(test_response)

    log.out.info("Done!")
