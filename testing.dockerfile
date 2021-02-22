FROM alpine:3.12 as build-stage-1

RUN apk update && \
  apk add --no-cache gcc g++ musl-dev geos geos-dev proj proj-dev proj-util gdal gdal-dev py3-numpy py3-numpy-dev python3 python3-dev py3-pip py3-psycopg2 py3-setuptools postgresql-dev

RUN pip3 install --upgrade pip && \
  pip3 install wheel && \
  pip3 install --no-cache-dir --prefix=/usr/local geoalchemy2==0.8.4 pyproj==2.6.1 shapely==1.7.1 geopandas==0.8.1 psycopg2==2.8.4

FROM alpine:3.12
ARG VERSION

RUN apk update && \
  apk add --no-cache geos-dev proj-util proj-datumgrid gdal-dev python3 python3-dev py3-pip py3-psycopg2 py3-setuptools py3-numpy

ENV VERSION="${VERSION}"
ENV PYTHON_VERSION="3.8"
ENV PYTHONPATH="/usr/local/lib/python${PYTHON_VERSION}/site-packages"

COPY --from=build-stage-1 /usr/local/ /usr/local/

COPY setup.py requirements.txt requirements-testing.txt ./
RUN pip3 install --upgrade pip && \
  pip3 install wheel && \
  pip3 install --no-cache-dir --prefix=/usr/local -r requirements.txt -r requirements-testing.txt

ENV FLASK_APP="geometry_service" \
    FLASK_ENV="testing" \
    FLASK_DEBUG="false"

COPY run-nosetests.sh /
RUN chmod a+x /run-nosetests.sh
ENTRYPOINT ["/run-nosetests.sh"]