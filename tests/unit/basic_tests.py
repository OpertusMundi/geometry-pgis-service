import logging
import json
from os import path, getenv
from fiona.errors import DriverError

# Setup/Teardown
def setup_module():
    print(" == Setting up tests for %s"  % (__name__))
    pass

def teardown_module():
    print(" == Tearing down tests for %s"  % (__name__))
    pass

# Tests