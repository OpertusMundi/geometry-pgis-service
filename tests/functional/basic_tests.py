import logging
import json
from os import path
from time import sleep
from uuid import uuid4

from geometry_service import create_app

# Setup/Teardown

app = create_app()

def setup_module():
    print(" == Setting up tests for %s"  % (__name__))
    app.config['TESTING'] = True
    print(" == Using database at %s"  % (app.config['SQLALCHEMY_DATABASE_URI']))
    pass

def teardown_module():
    print(" == Tearing down tests for %s"  % (__name__))
    pass

# Tests

def test_get_documentation_1():
    with app.test_client() as client:
        res = client.get('/', query_string=dict(), headers=dict())
        assert res.status_code == 200
        r = res.get_json();
        assert not (r.get('openapi') is None)
