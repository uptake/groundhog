FROM alpine:3.7
LABEL maintainer="jaylamb20@gmail.com"
LABEL author1="brad.beechler@uptake.com"
LABEL author2="jaylamb20@gmail.com"
LABEL website="https://github.com/uptake/groundhog"
LABEL description="groundhog is a service which provides access to SRTM elevation data."

####################
# SETUP            #
####################

# Add system libs
RUN apk add --update --no-cache \
    bash \
    build-base \
    ca-certificates \
    curl \
    curl-dev \
    g++ \
    gcc \
    glib \
    git \
    linux-headers \
    py-pip

# Hack to make docker always use bash instead of sh
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN pip install --upgrade pip && \
    pip install setuptools


####################
## PYTHON 3.X.
####################

RUN curl -L "https://github.com/andyshinn/alpine-pkg-glibc/releases/download/2.23-r1/glibc-2.23-r1.apk" -o /tmp/glibc.apk \
    && curl -L "https://github.com/andyshinn/alpine-pkg-glibc/releases/download/2.23-r1/glibc-bin-2.23-r1.apk" -o /tmp/glibc-bin.apk \
    && curl -L "https://github.com/andyshinn/alpine-pkg-glibc/releases/download/2.23-r1/glibc-i18n-2.23-r1.apk" -o /tmp/glibc-i18n.apk

RUN apk add --allow-untrusted /tmp/glibc*.apk \
    && /usr/glibc-compat/sbin/ldconfig /lib /usr/glibc-compat/lib \
    && /usr/glibc-compat/bin/localedef -i en_US -f UTF-8 en_US.UTF-8 \
    && rm -rf /tmp/glibc*apk /var/cache/apk/*

# From: https://github.com/frol/docker-alpine-miniconda3/blob/master/Dockerfile
ENV CONDA_DIR="/opt/conda"
ENV PATH="$CONDA_DIR/bin:$PATH"

# Install conda
RUN CONDA_VERSION="4.3.14" && \
    CONDA_MD5_CHECKSUM="fc6fc37479e3e3fcf3f9ba52cae98991" && \
    \
    apk add --no-cache --virtual=.build-dependencies wget ca-certificates bash && \
    \
    mkdir -p "$CONDA_DIR" && \
    wget "http://repo.continuum.io/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh" -O miniconda.sh && \
    echo "$CONDA_MD5_CHECKSUM  miniconda.sh" | md5sum -c && \
    bash miniconda.sh -f -b -p "$CONDA_DIR" && \
    echo "export PATH=$CONDA_DIR/bin:\$PATH" > /etc/profile.d/conda.sh && \
    rm miniconda.sh && \
    \
    conda update --all --yes && \
    conda config --set auto_update_conda False && \
    rm -r "$CONDA_DIR/pkgs/" && \
    \
    apk del --purge .build-dependencies && \
    \
    mkdir -p "$CONDA_DIR/locks" && \
    chmod 777 "$CONDA_DIR/locks"

####################
# groundhog code   #
####################

ENV WORKDIR /usr/local/groundhog

COPY . $WORKDIR

RUN cd $WORKDIR && conda env create -n groundhog -f app/env.yml

# Install srtm package from GitHub
# to get access to changes from http://bit.ly/2Atm5kp
RUN mkdir /usr/local/src && \
    cd /usr/local/src && \
    git clone https://github.com/tkrajina/srtm.py && \
    bash -c "source activate groundhog" && \
    cd /usr/local/src/srtm.py && \
    python setup.py install && \
    cd .. && \
    rm -rf srtm.py && \
    conda clean --all && \
    bash -c "source deactivate"

# Expose port 5005
EXPOSE 5005

# Spin up the app on "docker run" call
CMD source activate groundhog && python /usr/local/groundhog/app/groundhog.py
