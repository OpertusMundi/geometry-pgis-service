def add_components(spec):
    """Adds the service components to OpenAPI specification.

    Arguments:
        spec (obj): The apispec object.
    """
    import copy

    # Parameters

    spec.components.parameter('sessionToken', 'header', {
        "name": "X-Session-Token",
        "description": "A session unique token.",
        "required": True,
        "schema": {"type": "string"},
        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    })

    spec.components.parameter('label', 'path', {
        "name": "label",
        "description": "The dataset label.",
        "schema": {"type": "string"},
        "example": "my_dataset"
    })
    spec.components.parameter('page', 'query', {
        "name": "page",
        "description": "The requested page of the dataset.",
        "schema": {
            "type": "integer",
            "minimum": 1
        },
        "default": 1,
        "required": False,
    })
    spec.components.parameter('resultsPerPage', 'query', {
        "name": "results_per_page",
        "description": "The number of results for each page.<br/>**Note**: If this number is larger than a maximum value defined in the server, this maximum value is used instead.",
        "schema": {
            "type": "integer",
            "minimum": 1
        },
        "default": 10,
        "required": False,
    })


    # Schemata

    dataset_metadata = {
        "type": "object",
        "properties": {
            "epsg": {
                "description": "The EPSG code of the dataset's CRS.",
                "type": "integer",
                "example": 4326
            },
            "driver": {
                "description": "The driver that was used to read the uploaded file.",
                "type": "string",
                "example": "ESRI Shapefile"
            }
        }
    }
    spec.components.schema('datasetMetadata', dataset_metadata)

    ingest_form = {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "The label of the newly created dataset. Only lowercase latin characters and underscore are allowed.",
                "example": "my_dataset"
            },
            "delimiter": {
                "type": "string",
                "description": "In case the file is a delimited text file, the character used to separate values. Ignored for not delimited files.",
                "example": ";",
                "default": ","
            },
            "lat": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to latitude, if the geometry is given in means of lat, lon. Ignored for not delimited files.",
                "example": "latitude"
            },
            "lon": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to longitude, if the geometry is given in means of lat, lon. Ignored for not delimited files.",
                "example": "longitude"
            },
            "geom": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to WKT geometry. Default is 'WKT'; ignored for not delimited files **or** when 'lat', 'lon' are provided.",
                "example": "geometry"
            },
            "crs": {
                "type": "string",
                "description": "The Coordinate Reference System of the geometries. If not given, the CRS information is obtained by the dataset; **required for** spatial files that do not provide CRS information, e.g. CSV.",
                "example": "EPSG:4326"
            },
            "encoding": {
                "type": "string",
                "description": "The encoding of the file. If not given, the encoding is automatically detected.",
                "example": "UTF-8"
            },
            "resource": {
                "type": "string",
                "description": "A resolvable path to the spatial file. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "/datasets/shapefile.tar.gz"
            }
        },
        "required": ["label", "resource"]
    }
    spec.components.schema('ingestForm', ingest_form)
    ingest_form_multi = {**ingest_form, "properties": {**ingest_form["properties"], "resource": {
        "type": "string",
        "format": "binary",
        "description": "Stream of the spatial file. The file could be in compressed form: zipped or tar(.gz) archive."
    }}}
    spec.components.schema('ingestFormMultipart', ingest_form_multi)

    spec.components.schema('datasetExtendedInfo', {
        "type": "object",
        "description": "Information about the dataset.",
        "properties": {
            "label": {
                "type": "string",
                "description": "The label of the dataset.",
                "example": "first_dataset"
            },
            "created": {
                "type": "string",
                "format": "date-time",
                "description": "The creation datetime of the dataset.",
                "example": "Thu, 11 Feb 2021 12:55:51 GMT"
            },
            "bbox": {
                "type": "array",
                "description": "The bounding box of the dataset in the form [xmin, ymin, xmax, ymax]",
                "items": {
                    "type": "number",
                    "format": "float",
                    "description": "Coordinate"
                },
                "example": [6.4702796, 49.6904649, 6.5205999, 49.8154565]
            },
            "epsg": {
                "type": "integer",
                "description": "The EPSG code of the dataset.",
                "example": 4326
            },
            "features": {
                "type": "integer",
                "description": "The total number of features in the dataset.",
                "example": 19331
            },
            "driver": {
                "type": "string",
                "description": "The driver used to read the uploaded file. Null if the dataset was not created from file.",
                "example": "CSV"
            },
            "source": {
                "type": "string",
                "description": "The label of the source dataset, from which this was generated; null otherwise, i.e. in case the file was ingested to the system.",
                "example": "original_dataset"
            },
            "action": {
                "type": "string",
                "description": "The action that was performed over the source dataset, to generate the current dataset. Null if the dataset was not generated through an action.",
                "example": "constructive.centroid"
            }
        }
    })

    spec.components.schema('exportForm', {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "The label of the dataset to export. If not given, the *active* dataset will be exported.",
                "example": "my_dataset"
            },
            "driver": {
                "type": "string",
                "enum": ["CSV", "ESRI Shapefile", "GeoJSON", "GPKG", "MapInfo File", "DGN", "KML"],
                "description": "The driver which will be used to export the file. If not given, the driver of the source dataset will be assumed."
            },
            "crs": {
                "type": "string",
                "description": "The Coordinate Reference System of the geometries. If not given, the CRS of the source dataset will be assumed.",
                "example": "EPSG:4326"
            },
            "delimiter": {
                "type": "string",
                "description": "The character used to separate values in CSV format. Ignored if driver is not CSV.",
                "example": ";"
            },
            "name_field": {
                "type": "string",
                "description": "The attribute that will be used as the *name* field in KML format. Ignored if driver is not KML.",
                "default": "Name",
                "example": "name_en"
            },
            "description_field": {
                "type": "string",
                "description": "The attribute that will be used as the *description* field in KML format. Ignored if driver is not KML.",
                "default": "Description",
                "example": "description_en"
            },
            "encoding": {
                "type": "string",
                "description": "The encoding of the file.",
                "default": "UTF-8"
            },
            "copy_to_output": {
                "type": "boolean",
                "description": "When true, the exported file will be copied to output directory and will persist the destroy of the session.",
                "default": "false"
            },
        }
    })

    spec.components.schema('paginationInfo', {
        "type": "object",
        "description": "Information about the used pagination.",
        "properties": {
            "dataset": {
                "type": "string",
                "description": "The label of the dataset that is viewed.",
                "example": "my_dataset"
            },
            "page": {
                "type": "integer",
                "description": "The current page number.",
                "example": 99
            },
            "resultsPerPage": {
                "type": "integer",
                "description": "The maximum number of features for each page.",
                "example": 10
            },
            "hasMore": {
                "type": "boolean",
                "description": "Whether there are more results."
            }
        }
    })

    spec.components.schema('geoJSON', {
        "type": "object",
        "description": "GeoJSON corresponding to the given page of the dataset, with properties the dataset attributes.",
        "properties": {
            "type": {
                "type": "string",
                "value": "FeatureCollection",
                "example": "FeatureCollection"
            },
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "value": "Feature",
                            "example": "Feature"
                        },
                        "geometry": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Geometry type",
                                    "example": "Point"
                                },
                                "coordinates": {
                                    "type": "array",
                                    "description": "The array shape depends on the type of geometry.",
                                    "items": {
                                        "anyOf": [
                                            {"type": "number", "format": "float"},
                                            {"type": "array", "items": {"anyOf": [{"type": "number", "format": "float"}, {"type": "array", "items": {"type": "float"}}]}}
                                        ]
                                    },
                                    "example": [6.1659779, 49.6150126]
                                }
                            }
                        },
                        "properties": {
                            "type": "object",
                            "description": "The key is the attribute name",
                            "additionalProperties": {
                                "anyOf": [{"type": "string"}, {"type": "number", "format": "float"}, {"type": "integer"}]
                            },
                            "example": {"id": 981, "name": "example"}
                        }
                    }
                }
            }
        }
    })

    filter_form = {
        "type": "object",
        "properties": {
            "src": {
                "type": "string",
                "description": "The label of the dataset upon which the filter will be applied. If not given, the **active** dataset will be used.",
                "example": "original_dataset"
            },
            "label": {
                "type": "string",
                "description": "The label of the newly created dataset.",
                "example": "filtered_dataset"
            },
            "wkt": {
                "type": "string",
                "description": "The Well-Known-Text representation of the geometry to filter with.",
                "example": "POLYGON((6.4 49., 6.5 50., 6.6 49.5, 6.4 49.))"
            },
            "crs": {
                "type": "string",
                "description": "The CRS of the given geometry. If not given, the dataset CRS will be assumed.",
                "example": "EPSG:4326"
            }
        },
        "required": ["label", "wkt"]
    }
    spec.components.schema('filterForm', filter_form)
    filter_form = {**filter_form, "properties": {**filter_form["properties"], "wkt": {
        "type": "string",
        "format": "binary",
        "description": "A text file containing the Well-Known-Text representation of the geometry to filter with."
    }}}
    spec.components.schema('filterFormMultipart', filter_form)

    filter_buffer_form = copy.deepcopy(filter_form)
    del filter_buffer_form['properties']['wkt']
    filter_buffer_form['properties']['center_x'] = {
        "type": "number",
        "format": "float",
        "description": "The x-coordinate of the center point. For geodetic coordinates, it is the longitude of the center point.",
        "example": 6.47
    }
    filter_buffer_form['properties']['center_y'] = {
        "type": "number",
        "format": "float",
        "description": "The y-coordinate of the center point. For geodetic coordinates, it is the latitude of the center point.",
        "example": 49.69
    }
    filter_buffer_form['properties']['radius'] = {
        "type": "number",
        "format": "float",
        "description": "The radius from the center point that the geometries should lie within. The radius is specified in units defined by the srid.",
        "example": 0.1
    }
    filter_buffer_form['required'] = ["label", "center_x", "center_y", "radius"]
    spec.components.schema('filterBufferForm', filter_buffer_form)

    constructive_form = {
        "type": "object",
        "properties": {
            "src": {
                "type": "string",
                "description": "The label of the dataset upon which the filter will be applied. If not given, the **active** dataset will be used.",
                "example": "original_dataset"
            },
            "label": {
                "type": "string",
                "description": "The label of the newly created dataset.",
                "example": "new_dataset"
            }
        },
        "required": ["label"]
    }
    spec.components.schema('constructiveForm', constructive_form)

    join_form = {
        "type": "object",
        "properties": {
            "left": {
                "type": "string",
                "description": "The label of the dataset upon which the other (*right*) dataset will be joined. If not given, the **active** dataset will be used.",
                "example": "left_dataset"
            },
            "right": {
                "type": "string",
                "description": "The label of the dataset which will be joined to the *left* dataset.",
                "example": "right_dataset"
            },
            "label": {
                "type": "string",
                "description": "The label of the newly created dataset.",
                "example": "new_dataset"
            },
            "join_type": {
                "type": "string",
                "enum": ["inner", "outer"],
                "default": "outer",
                "description": "The type of the join."
            }
        },
        "required": ["left", "right", "label"]
    }
    spec.components.schema('joinForm', join_form)

    join_distance_form = {**join_form, "properties": {**join_form['properties'], "distance": {
        "type": "number",
        "format": "float",
        "description": "The distance that the two geometries should be within. It is specified in units defined by the srid of the *left* dataset.",
        "example": 4.3
    }}, "required": [*join_form['required'], "distance"]}
    spec.components.schema('joinDistanceForm', join_distance_form)


    # Responses

    spec.components.response('newDatasetResponse', {
        "description": "A new dataset is generated.",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/datasetMetadata"
                }
            }
        }
    })

    validation_error_response = {
        "description": "Form validation error.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "description": "The key is the request body key.",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Description of validation error."
                        }
                    },
                    "example": {
                        "label": [
                            "Field must be unique for the session."
                        ]
                    }
                }
            },
            "text/plain": {
                "schema": {
                    "type": "string",
                    "description": "No active dataset."
                }
            }
        }
    }
    spec.components.response('validationErrorResponse', validation_error_response)

    spec.components.response('noSessionResponse', {
        "description": "No session token provided, or the session token does not correspond to an active session.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Error message",
                            "example": "No session token found."
                        }
                    }
                }
            }
        }
    })

    spec.components.response('deferredResponse', {
        "description": "Request accepted for process.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "ticket": {
                            "type": "string",
                            "description": "The unique ticket assigned to the request.",
                            "example": "caff960ab6f1627c11b0de3c6406a140"
                        },
                        "statusUri": {
                            "type": "string",
                            "description": "The URI to poll for the status of the request.",
                            "example": "/jobs/status?ticket=caff960ab6f1627c11b0de3c6406a140"
                        }
                    }
                }
            }
        }
    })

    spec.components.response('exportsListResponse', {
        "description": "A list with the exports requested in the session.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "The label of the dataset.",
                                "example": "my_dataset"
                            },
                            "exports": {
                                "type": "array",
                                "description": "A list of exports for this specific dataset.",
                                "items": {
                                    "type": "object",
                                    "description": "The export details for a specific driver",
                                    "properties": {
                                        "driver": {
                                            "type": "string",
                                            "description": "The driver used for the export.",
                                            "enum": ["CSV", "ESRI Shapefile", "GeoJSON", "GPKG", "MapInfo File", "DGN", "KML"]
                                        },
                                        "link": {
                                            "type": "string",
                                            "description": "The link to download the export.",
                                            "example": "/dataset/download/my_dataset.csv.gz"
                                        },
                                        "output_path": {
                                            "type": "string",
                                            "description": "The location of the export in the output directory (null if copy to output path has not been requested).",
                                            "example": "2102/{token}/{ticket}/my_dataset.csv.gz"
                                        },
                                        "status": {
                                            "type": "string",
                                            "description": "The status of the export.",
                                            "enum": ["completed", "processing", "failed"]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    spec.components.response('datasetNotFoundResponse', {
        "description": "Does not exist yet, possibly because there is no active dataset in the session.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Error message",
                            "example": "No active dataset found."
                        }
                    }
                }
            }
        }
    })
