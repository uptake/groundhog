#!/bin/bash

# Failure is a natural part of life
set -e

# Set up environment variables
export CRAN_MIRROR=http://cran.rstudio.com
export MINICONDA_INSTALLER=https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Install conda
wget ${MINICONDA_INSTALLER} -O miniconda.sh;
bash miniconda.sh -b -p ${CONDA_DIR}
echo "export PATH=${CONDA_DIR}/bin:$PATH" >> ${HOME}/.bashrc

${CONDA_DIR}/bin/conda config --set always_yes yes --set changeps1 no
${CONDA_DIR}/bin/conda update -q conda
${CONDA_DIR}/bin/conda info -a

# Set up R (gulp)
${CONDA_DIR}/bin/conda install -c r \
    r-assertthat \
    r-data.table \
    r-jsonlite \
    r-r6 \
    r-uuid

${CONDA_DIR}/bin/conda install -c conda-forge \
    r-covr \
    r-futile.logger

# Per https://github.com/ContinuumIO/anaconda-issues/issues/9423#issue-325303442,
# packages that require compilation may fail to find the
# gcc bundled with conda
export PATH=${PATH}:${CONDA_DIR}/bin

# Get Python packages for testing
${CONDA_DIR}/bin/conda install \
    --yes \
        requests \
        pandas
