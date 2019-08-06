from requests import post
import pandas as pd
import json
from uuid import uuid4


class GroundhogClient:
    """
    groundhog client that deals with negotiating withe the
    groundhog API.
    """

    def __init__(self, host_name='localhost', port=5005):
        assert isinstance(host_name, str)
        assert isinstance(port, int)
        self.host_name = host_name
        self.port = port
        self.url = "http://{}:{}/groundhog".format(self.host_name, self.port)

    def get_query(self, payload_json):
        assert isinstance(payload_json, list)
        headers = {'Content-Type': 'application/json'}
        response = post(self.url, headers=headers, data=json.dumps(payload_json))
        return(response.json())

    def get_df(self, payload_json):
        """
        Get a pandas DataFrame representation of a query result.
        """
        response_df = pd.DataFrame.from_records(self.get_query(payload_json))[['bearing', 'slope', 'elevation', 'unique_key']]
        assert response_df.shape[0] == len(payload_json)
        return(response_df)


def _get_payload_json(df):
    """
    Given a pandas DataFrame, create a query body to send
    to groundhog.
    """
    assert 'latitude' in df.columns
    assert 'longitude' in df.columns
    assert 'dateTime' in df.columns
    # Sort by date_time so slope makes sense
    df.sort_values(by='dateTime',
                   ascending=True,
                   inplace=False)
    if 'bearing' in df.columns:
        out = df[['longitude', 'latitude', 'bearing', 'unique_key']].to_dict(orient='records')
    else:
        out = df[['longitude', 'latitude', 'unique_key']].to_dict(orient='records')
    return(list(out))


def append_slope_features(df, host_name, port):
    """
    Append slope features from groundhog to a pandas
    dataframe.
    """
    # Create a client
    client = GroundhogClient(host_name=host_name, port=port)

    # Generate a sorted list of unique_key uuids
    # The sorting guarantees that we can sort the result later and
    # subset out of it to do an in-place append onto the original df
    num_rows = df.shape[0]
    join_keys = list(map(lambda x: str(uuid4()), range(num_rows)))
    join_keys.sort()
    df['unique_key'] = join_keys

    # Get API payload for each asset's data
    payloads = [_get_payload_json(df[df['assetId'] == asset]) for asset in df.assetId.unique()]

    # Loop over payloads and get responses
    response_df = pd.concat([client.get_df(pl) for pl in payloads],
                            ignore_index=True)

    # Sort in ascending order by unique_key
    response_df.sort_values(by='unique_key',
                            ascending=True,
                            inplace=True)

    # Append columns to original df
    for col in ['bearing', 'slope', 'elevation']:
        if col not in df.columns:
            df[col] = response_df[col]
