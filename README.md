
# groundhog

Our mission:

> Things go up. And down. We might be able to make money by telling people when that happened.

Our motto:

> If you ain't first, you're last.

### Building the container

We'll put the container up on Dockerhub soon ([status](https://github.com/uptake/groundhog/issues/24)). For now, you can build locally from this repo.

```bash
git clone https://github.com/uptake/groundhog.git
cd groundhog
docker build -t groundhog -f Dockerfile-app .
```

### Running the app

Run this command to kick up a local version of the app

```bash
docker run -p 5005:5005 --name groundhog_server groundhog
```

You can now hit the API on `localhost`. Run the following command in a separate terminal to see the help docs.

```bash
curl http://localhost:5005
```

To stop the container by name (if you used the `--name` tag when launching it), do the following:

```bash
docker stop groundhog_server
```

### R client

We provide an R client for the service. Given a `data.table` with GPS information and (optionally) bearing, this client will use `groundhog` to enrich that dataset with elevation and slope features.

You can install the package from source

```bash
R CMD INSTALL r-client/
```

To test it out, spin up a local version of the service, then run this example:

```r
library(data.table)

someDT <- data.table::data.table(
    longitude = runif(10, -110, -109)
    , latitude = runif(10, 45, 46)
    , dateTime = seq.POSIXt(from = as.POSIXct("2017-01-01", tz = "UTC")
                             , to = as.POSIXct("2017-01-15", tz = "UTC")
                             , length.out = 10)
    , assetId = c(rep("ABC", 5), rep("DEF", 5))
)

groundhog::append_slope_features(someDT, hostName = "localhost", port = 5005)
```

### Python client

We provide a Python client for the service. Given a `pandas` `DataFrame` with GPS information and (optionally) bearing, this client will use `groundhog` to enrich that dataset with elevation and slope features.

You can install the package from source

```bash
pushd py-client
    pip install .
popd
```

To test it out, spin up a local version of the service, then run this example:

```python
import pandas as pd
import numpy as np
import groundhog as gh

some_df = pd.DataFrame({
    "longitude": -110 + np.random.rand(10),
    "latitude": 45 + np.random.rand(10),
    "dateTime": pd.date_range(pd.datetime.today(), periods=10),
    "assetId": ["ABC"]*5 + ["DEF"]*5
    })

gh.append_slope_features(some_df, host_name="localhost", port=5005)
```

### Background

This project is built on top of [srtm.py](https://github.com/tkrajina/srtm.py), a Python library that makes the SRTM data accessible and easy to query.
