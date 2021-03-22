# Geometry-Service

## Description

The *geometry service* offers the ability to apply geometric operations on one or more spatial files. Multiple geometric operations can be, in general, consecutively applied, before the final resulted file is exported and downloaded.

A PostGIS database is used to ingest files into and perform the spatial operations. The spatial files are read with GeoPandas / Fiona (python bindings to GDAL). Pandas recognizes the data types of the attributes and creates the corresponding table to PostGIS. Each time a spatial operation is requested, a new *view* is created in the database.

The service uses sessions to store the ingested and generated datasets. Each session is associated with a session token, and the related datasets are available only within this session. Almost every request to this service should transfer this token in its header. A session is automatically created when the first spatial file is ingested.

Following the ingestion of a file, one can apply geometric operations in order to generate new datasets, or ingest more. Each dataset is associated with a user-defined *label*, which should be unique for the session. The user can choose upon which dataset is willing to apply each operation by choosing the corresponding label. Every session has one active dataset, which has the role to be the one used by default in cases that no label is supplied with the request. The active dataset is, in principle, the last ingested dataset, unless it has explicitly changed.

The session and all the related datasets are destroyed upon request or if the session remains idle for a certain amount of time.

## Installation

### Dependencies

* Python 3.8
* Running instance of PostgreSQL / PostGIS
* [GEOS library](https://github.com/libgeos/geos)
* [PROJ 7](https://proj.org)
* [GDAL 3.1](https://gdal.org/download.html#binaries)

### Install package

Install with pip:
```
pip install git+https://github.com/OpertusMundi/geometry-service.git
```
Install separately the Python required packages:
```
pip install -r requirements.txt -r requirements-production.txt
```
### Set environment

The following environment variables should be set:
* `FLASK_ENV`<sup>*</sup>: `development` or `production`.
* `FLASK_APP`<sup>*</sup>: `geometry_service` (if running as a container, this will be always set).
* `SECRET_KEY`<sup>*</sup>: The application secret key.
* `DATABASE_URI`<sup>*</sup>: `postgresql://user:pass@host:port/database`
* `WORKING_DIR` : The location for storing the session files (*default*: the system temporary path).
* `OUTPUT_DIR`<sup>*</sup>: The location used to store exported files.
* `CORS`: List or string of allowed origins (*default*: '*').
* `LOGGING_CONFIG_FILE`<sup>*</sup>: The logging configuration file.
* `TOKEN_HEADER`: The header used for the session token (*default*: 'X-Token').
* `CLEANUP_INTERVAL`: If a session remains idle for this time interval, it is considered as inactive and all data associated with it (database tables/views and files) are cleaned (in minutes; *default*: 1440).
* `MAX_RESULTS_PAGE`: The maximum results per page for the paginated views (*default*: 50).

<sup>*</sup> Required.

### Database

A database should have been created in a PostgreSQL server, with PostGIS extension enabled.

Initialize the database, running:
```
flask db upgrade
```

## Usage

For details about using the service API, you can browse the full [OpenAPI documentation](https://opertusmundi.github.io/geometry-pgis-service/).

## Build and run as a container

Copy `.env.example` to `.env` and configure (e.g `FLASK_ENV` variable).

Copy `compose.yml.example` to `compose.yml` (or `docker-compose.yml`) and adjust to your needs (e.g. specify volume source locations etc.).

Build:

    docker-compose -f compose.yml build

Prepare the following files/directories:

   * `./secrets/secret_key`: file needed (by Flask) for signing/encrypting session data.
   * `./secrets/postgres/password`: file containing the password for the PostGIS database user.
   * `./logs`: a directory to keep logs.
   * `./temp`: a directory to be used as temporary storage.
   * `./output`: a directory to be used to store exported files.

Start application:

    docker-compose -f compose.yml up


## Run tests

Copy `compose-testing.yml.example` to `compose-testing.yml` and adjust to your needs. This is a just a docker-compose recipe for setting up the testing container.

Run nosetests (in an ephemeral container):

    docker-compose -f compose-testing.yml run --rm --user "$(id -u):$(id -g)" nosetests -v
