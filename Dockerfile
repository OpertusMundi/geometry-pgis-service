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

LABEL language="python"
LABEL framework="flask"
LABEL usage="apply geometric operations on spatial files"

ENV VERSION="${VERSION}"
ENV PYTHON_VERSION="3.8"
ENV PYTHONPATH="/usr/local/lib/python${PYTHON_VERSION}/site-packages"

RUN addgroup flask && adduser -h /var/local/geometry_service -D -G flask flask

COPY --from=build-stage-1 /usr/local/ /usr/local/

RUN mkdir /usr/local/geometry_service/
COPY setup.py requirements.txt requirements-production.txt /usr/local/geometry_service/
COPY geometry_service /usr/local/geometry_service/geometry_service

RUN pip3 install --upgrade pip && \
  pip3 install wheel && \
  (cd /usr/local/geometry_service && pip3 install --no-cache-dir --prefix=/usr/local -r requirements.txt -r requirements-production.txt)
RUN cd /usr/local/geometry_service && python3 setup.py install --prefix=/usr/local && python3 setup.py clean -a

RUN ln -s $(which python3) /usr/bin/python

COPY wsgi.py docker-command.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/wsgi.py /usr/local/bin/docker-command.sh

WORKDIR /var/local/geometry_service
RUN mkdir ./logs && chown flask:flask ./logs
COPY --chown=flask logging.conf .

ENV FLASK_APP="geometry_service" \
    FLASK_ENV="production" \
    FLASK_DEBUG="false" \
    TLS_CERTIFICATE="" \
    TLS_KEY=""

USER flask
CMD ["/usr/local/bin/docker-command.sh"]

EXPOSE 5000
EXPOSE 5443
