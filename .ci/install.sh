#!/bin/bash

# failure is a natural part of life
set -e

PY_DIR=$(pwd)/py-client
R_DIR=$(pwd)/r-client

pushd ${PY_DIR}
    python setup.py install
popd

pushd ${R_DIR}

    ${CONDA_DIR}/bin/R CMD INSTALL .
popd
