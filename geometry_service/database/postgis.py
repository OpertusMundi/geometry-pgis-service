import geopandas as gpd
import fiona
import pandas as pd
from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
import shapely
import os
import warnings
from geometry_service.exceptions import CRSNotFound
from geometry_service.loggers import logger


class Postgis(object):
    """Creates a connection to PostgreSQL / PostGIS database.

    Attributes:
        engine (obj): The SQLAlchemy pool and dialect to database.
        schema (str): The active database schema.
    """

    def __init__(self, schema):
        """The postgres constructor, initiates a (lazy) connection.

        Arguments:
            schema (str): The active schema for the session.
        """
        database_url = os.environ['DATABASE_URI']
        self.engine = create_engine(database_url)
        self.schema = schema
        logger.debug('Postgis initiated.')


    def check(self):
        """Checks the connection to database.

        Returns:
            (str): On success, the database uri.
        """
        with self.engine.connect() as con:
            con.execute('SELECT 1')
        return self.engine.url


    def checkIfTableExists(self, table):
        """Check if a table exists in the schema.

        Arguments:
            table (str): The table name.

        Returns:
            (bool): True if exists.
        """
        with self.engine.connect() as con:
            cur = con.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = '%s' AND table_name = '%s');" % (self.schema, table))
            exists = cur.fetchone()[0]
        return exists


    def ingest(self, file, table, chunksize=100000, commit=True, crs=None, lat=None, lon=None, geom='WKT', delimiter=',', **kwargs):
        """Creates a DB table and ingests a vector file into it.

        It reads a vector file with geopandas (fiona) and writes the attributes and geometry into a database table. A spatial index will also be created.

        Arguments:
            file (str): The path of the vector file.
            table (str): The table name (it will be created if does not exist).
            **kwargs: Other keyword arguments for the file reader, depending on the driver.

        Keyword Arguments:
            chunksize (int): Number of records that will be read from the file in each turn (default: {100000}).
            commit (bool): Whether to commit the transanction after ingesting or not, e.g., for testing purposes (default: {True}).
            crs (str): The CRS of the spatial file. If not given, the CRS will be extracted from the file. (Required if the file does not carry this information; default: {None}.)
            lat (str): The latitude field name in delimited files, ignored in all other cases (default: {None}).
            lon (str): The longitude field name in delimited files, ignored in all other cases (default: {None}).
            geom (str): The (WKT) geometry field name in delimited files, ignored in all other cases (default: {'WKT'}).
            delimiter (str): The delimiter character in case of CSV (default: {','}).

        Raises:
            CRSNotFound: CRS not found.

        Returns:
            (tuple):
                * (str) The created table name,
                * (dict) General information about the dataset: the driver which used to open the file, epsg number, and the number of features.
        """
        import pyproj
        schema = self.schema
        file = self._extract_file(file)
        extension = os.path.splitext(file)[1]
        if extension == '.kml':
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'r'
        eof = False
        i = 0
        rows = 0
        if crs is not None:
            crs = pyproj.crs.CRS.from_user_input(crs).to_epsg()
        with self.engine.connect() as con:
            trans = con.begin()
            if file.endswith('.csv'):
                driver = 'CSV'
                logger.debug('Starting ingestion [file: "%s", driver: "CSV"]', file)
                if crs is None:
                    raise CRSNotFound('CRS info cannot be retrieved.')
                if_exists = 'fail'
                for df in pd.read_csv(file, chunksize=chunksize, delimiter=delimiter, **kwargs):
                    if lat is not None and lon is not None:
                        df['geom'] = df.apply(lambda elem: WKTElement(shapely.wkt.dumps(shapely.geometry.Point(elem[lon], elem[lat])), srid=crs), axis=1)
                        gtype = 'POINT'
                    else:
                        df['geom'] = df[geom].apply(lambda x: WKTElement(x, srid=crs))
                        gtype = 'GEOMETRY'
                    df.drop(geom, 1, inplace=True)
                    df.to_sql(table, con=con, schema=schema, if_exists=if_exists, index=False, dtype={'geom': Geometry(gtype, srid=crs)})
                    rows += len(df)
                    if_exists = 'append'
            else:
                c = fiona.open(file, rows=slice(0,1))
                driver = c.driver
                c.close()
                logger.debug('Starting ingestion [file: "%s", driver: "%s"]', file, driver)
                while eof == False:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=RuntimeWarning)
                        df = gpd.read_file(file, rows=slice(i*chunksize, (i+1)*chunksize), **kwargs)
                        length = len(df)
                        if length == 0:
                            eof = True
                            continue
                        rows = rows + length
                        epsg = df.crs.to_epsg() if crs is None and df.crs is not None else crs
                        if epsg is None:
                            raise CRSNotFound('CRS info cannot be retrieved.')
                        if extension == '.kml':
                            df.geometry = df.geometry.map(lambda polygon: shapely.ops.transform(lambda x, y: (x, y), polygon))
                        df['geom'] = df['geometry'].apply(lambda x: WKTElement(x.wkt, srid=epsg))
                        if i == 0:
                            gtype = df.geometry.geom_type.unique()
                            if len(gtype) == 1:
                                gtype = gtype[0]
                            else:
                                gtype = 'GEOMETRY'
                            if_exists = 'fail'
                        else:
                            if_exists = 'append'
                        df.drop('geometry', 1, inplace=True)
                        df.to_sql(table, con=con, schema=schema, if_exists=if_exists, index=False, dtype={'geom': Geometry(gtype, srid=epsg)})
                        i += 1
                crs = epsg

            # bbox = con.execute("SELECT ST_AsGeoJSON(ST_Extent(geom), 8, 1)::jsonb FROM {0}.{1}".format(schema, table)).scalar()
            # if bbox is not None:
            #     bbox = bbox['bbox']

            if commit:
                trans.commit()
                logger.debug('Ingested dataset to PostGIS. [file: "%s", table: "%s", driver: "%s", epsg: %i, features: %i]', file, table, driver, crs, rows)
            else:
                trans.rollback()
            trans.close()

        return (table, {'driver': driver, 'epsg': crs})


    def view(self, table, page=1, results_per_page=10):
        """Returns paginated data for a table in tabular format.

        Arguments:
            table (str): The table name.

        Keyword Arguments:
            page (number): The requested page number (default: {1})
            results_per_page (number): The number of resulst per page (default: {10})

        Returns:
            (dict): A dictionary with information about pagination, and the data in tabular format.
        """
        with self.engine.connect() as con:
            rows = con.execute(
                "SELECT *, ST_AsText(geom, 8) as geom FROM {schema}.{table} LIMIT {limit} OFFSET {offset}"
                .format(schema=self.schema, table=table, limit=results_per_page, offset=results_per_page * (page - 1))
            )
            row = rows.fetchone()
            data = []
            while row is not None:
                data.append(dict(zip(row.keys(), row)))
                row = rows.fetchone()
        has_more = self._has_more(table, page, results_per_page)
        return {'info': {'dataset': table, 'page': page, 'resultsPerPage': results_per_page, 'hasMore': has_more}, 'data': data}


    def geojson(self, table, page=1, results_per_page=10):
        """Returns paginated data for a table in GeoJSON format.

        Arguments:
            table (str): The table name.

        Keyword Arguments:
            page (number): The requested page (default: {1})
            results_per_page (number): The number of results per page (default: {10})

        Returns:
            (dict): A dictionary with information about pagination, and the data in GeoJSON format.
        """
        with self.engine.connect() as con:
            data = con.execute(
                "WITH subset as (SELECT * FROM {schema}.{table} LIMIT {limit} OFFSET {offset}) SELECT json_build_object('type', 'FeatureCollection', 'features', json_agg(json_build_object('type', 'Feature', 'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json, 'properties', to_jsonb(subset) - 'geom'))) FROM subset"
            .format(schema=self.schema, table=table, limit=results_per_page, offset=results_per_page * (page - 1))
            ).scalar()
        has_more = self._has_more(table, page, results_per_page)
        return {'info': {'dataset': table, 'page': page, 'resultsPerPage': results_per_page, 'hasMore': has_more}, 'data': data}


    def _has_more(self, table, page, results_per_page):
        offset = results_per_page * page
        with self.engine.connect() as con:
            row = con.execute("SELECT * FROM {schema}.{table} LIMIT 1 OFFSET {offset}".format(schema=self.schema, table=table, offset=offset)).fetchone()
        return False if row is None else True


    def to_file(self, table, path, driver, filename=None, **kwargs):
        """Extracts a PostGIS spatial table to file.

        Reads the table in chunks with geopandas, and appends the dataframe to file. Depending on the driver, more than one file can be required to describe the dataset. In all cases, the resulted file(s) will be compressed.

        Arguments:
            table (str): The table name.
            path (str): The full destination path.
            driver (str): The GDAL driver which will be used to export the file.
            **kwargs: Additional keyword arguments used for the file reader.

        Keyword Arguments:
            filename (str): The filename of the exported file. If None, the table name will be used (default: {None})

        Returns:
            (str): The full path of the compressed exported file(s).
        """
        chunksize = kwargs.pop('chunksize', 100)
        encoding = kwargs.pop('encoding', None)
        name_field = kwargs.pop('name_field', 'Name')
        description_field = kwargs.pop('description_field', 'Description')
        sep = kwargs.pop('delimiter', ',')
        crs = kwargs.pop('crs', None)
        filename = table if filename is None else table
        extensions = {'GeoJSON': '.geojson', 'GPKG': '.gpkg'}

        gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'raw'
        if driver in extensions.keys():
            filename = filename + extensions[driver]
        with self.engine.connect() as con:
            counter = 0
            mode = 'w'
            for gdf in gpd.read_postgis("SELECT * FROM {0}.{1}".format(self.schema, table), con, chunksize=chunksize, crs=crs, **kwargs):
                if driver == 'KML':
                    file = os.path.join(path, "{0}_{1}.kml".format(filename, counter))
                    gdf.to_file(file, driver=driver, mode='w', NameField=name_field, DescriptionField=description_field, encoding=encoding)
                    counter += 1
                elif driver == 'CSV':
                    file = os.path.join(path, filename + '.csv')
                    df = pd.DataFrame(gdf)
                    df.to_csv(file, sep=sep, mode=mode, encoding=encoding)
                else:
                    if driver == 'MapInfo File':
                        for col in gdf.columns:
                            if str(gdf[col].dtype)[0:3] == 'int':
                                gdf[col] = gdf[col].astype('float')
                    file = os.path.join(path, filename)
                    gdf.to_file(file, driver=driver, mode=mode, crs=crs, encoding=encoding)
                mode = 'a'

        logger.debug('Exported table to file. [table="%s", file="%s", driver="%s"]', table, file, driver)

        return self._compress_files(file)


    def create_view_action(self, name, table, action, column='geom', args=None):
        """Creates a new view in database schema from a table, by applying an action on a column of the table.

        Arguments:
            name (str): The name which will be given to the view.
            table (str): The name of the table.
            action (str): The SQL function that will be applied to the column of the table.

        Keyword Arguments:
            column (str): The column of the table upon which the action will be applied (default: {'geom'})
            args (list): Additional arguments for the SQL function (default: {None})
        Returns:
            (str): Name of the created view.
        """
        columns = self.retrieve_columns(table, exclude=column)
        columns = '"' + '", "'.join(columns) + '"'
        arg = column if args is None else "{}, {}".format(column, ", ".join(args))
        sql = "CREATE VIEW {schema}.{name} AS (SELECT {columns}, {action}({arg})::geometry AS geom FROM {schema}.{table})" \
            .format(schema=self.schema, name=name, table=table, columns=columns, action=action, arg=arg)

        return self._create_view(sql, name)


    def create_view_filter(self, name, table, filter_, arg, column='geom'):
        """Creates a new view in database schema from a table, applying a spatial filter on the geometry column.

        Arguments:
            name (str): The name which will be given to the view.
            table (str): The name of the table.
            filter_ (str): The SQL function that will be used to filter the table.
            arg (str): The argument for the SQL function.

        Keyword Arguments:
            column (str): The column of the table which will be used to filter the table (default: {'geom'})

        Returns:
            (str): Name of the created view.
        """
        sql = "CREATE VIEW {schema}.{name} AS (SELECT * FROM {schema}.{table} WHERE {filter}({column}, {arg}))" \
            .format(schema=self.schema, name=name, table=table, filter=filter_, column=column, arg=arg)

        return self._create_view(sql, name)


    def create_view_join(self, name, left, right, action, join_type='outer', args=None, left_col='geom', right_col='geom', srid=None):
        """Creates a view in database schema, joining two tables on the result of an action condition.

        Arguments:
            name (str): The name which will be given to the view.
            left (str): The name of the main table in the join.
            right (str): The name of the table to join with.
            action (str): The action to apply.

        Keyword Arguments:
            join_type (str): The type of join: 'inner' or 'outer' (default: {'outer'})
            args (list) A list of additional arguments for the action (default: {None})
            left_col (str): The name of the column of the left table that the join will be performed on (default: {'geom'})
            right_col (str): The name of the column of the right table that the join will be performed on (default: {'geom'})
            srid (int): Transform the right geometry column to this srid, if it is not None (default: {None})

        Returns:
            (str): Name of the created view.
        """
        columns_from_left = map(lambda elem: '"{elem}" AS "{table}_{elem}"'.format(elem=elem, table=left), self.retrieve_columns(left, exclude=left_col))
        columns_from_left = ', '.join(columns_from_left)
        columns_from_right = map(lambda elem: '"{elem}" AS "{table}_{elem}"'.format(elem=elem, table=right), self.retrieve_columns(right, exclude=right_col))
        columns_from_right = ', '.join(columns_from_right)
        join_type = join_type.upper()
        join_type = 'LEFT' if join_type == 'OUTER' else join_type
        right_col = "{right}.{right_col}".format(right=right, right_col=right_col)
        if srid is not None:
            right_col = "ST_Transform({right_col}, {srid})".format(right_col=right_col, srid=srid)
        arg = '' if args is None else ", {}".format(", ".join(map(lambda elem: str(elem), args)))
        sql = "CREATE VIEW {schema}.{name} AS (SELECT {columns_from_left}, {columns_from_right}, {left}.{left_col} FROM {schema}.{left} {join_type} JOIN {schema}.{right} ON {action}({left}.{left_col}, {right_col}{arg}))" \
            .format(schema=self.schema, name=name, left=left, right=right, columns_from_left=columns_from_left, columns_from_right=columns_from_right, join_type=join_type, action=action, left_col=left_col, right_col=right_col, arg=arg)

        return self._create_view(sql, name)


    def _create_view(self, sql, name):
        """Creates a view in database schema from an sql statement.

        Arguments:
            sql (str): The sql that creates the view.
            name (str): The name of the view.

        Returns:
            (str): Name of the created view.
        """
        with self.engine.connect() as con:
            con.execute(sql)
        logger.debug('Created view. [sql="%s"]', sql)

        return name


    def retrieve_columns(self, table, exclude=None):
        """Retrieves the column names of a table in the schema.

        Arguments:
            table (str): The name of the table.

        Keyword Arguments:
            exclude (list|str): The table(s) to exclude (default: {None})

        Returns:
            (list): The list of the column names.
        """
        with self.engine.connect() as con:
            sql = "SELECT json_agg(column_name) FROM information_schema.columns WHERE table_schema = '{0}' AND table_name = '{1}'".format(self.schema, table)
            if exclude is not None:
                if isinstance(exclude, list):
                    sql += " AND column_name NOT IN ('{0}')".format("', '".join(exclude))
                elif isinstance(exclude, str):
                    sql += " AND column_name != '{0}'".format(exclude)
            columns = con.execute(sql).scalar()
        return columns


    def _extract_file(self, file):
        """Extracts a compressed archive.

        It extracts zipped and tar files. In case the file is neither of them, it returns the same file.

        Arguments:
            file (str): The full path of the file.

        Returns:
            (str): The path of the extracted folder, or the file if it was not compressed.
        """
        import zipfile
        import tarfile
        path, filename = os.path.split(file)
        if tarfile.is_tarfile(file):
            handle = tarfile.open(file)
            file = os.path.join(path, os.path.splitext(filename)[0])
            handle.extractall(file)
            handle.close()
        elif zipfile.is_zipfile(file):
            tgt = os.path.join(path, os.path.splitext(filename)[0])
            with zipfile.ZipFile(file, 'r') as handle:
                handle.extractall(tgt)
            file = tgt
        return file


    def _compress_files(self, path):
        """Compress files to tar.gz

        All the files contained in a folder will be added to the archive.

        Arguments:
            path (str): The full path of the folder containing the files that will be added to the archive.

        Returns:
            (str): The archived file.
        """
        import tarfile
        if os.path.isdir(path):
            result = path + '.tar.gz'
            with tarfile.open(result, "w:gz") as tar:
                for file in os.listdir(path):
                    tar.add(os.path.join(path, file), arcname=file)
        else:
            result = path + '.gz'
            with tarfile.open(result, "w:gz") as tar:
                tar.add(path, arcname=path)

        return result
