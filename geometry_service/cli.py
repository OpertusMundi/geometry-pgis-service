from flask import current_app as app
import click

@app.cli.command()
def cleanup():
    """Set idle sessions as inactive and clean their data."""
    import os
    from datetime import datetime, timedelta
    from shutil import rmtree
    from geometry_service.database import db
    from geometry_service.database.model import Session

    interval = int(os.environ['CLEANUP_INTERVAL'])
    time = datetime.now() - timedelta(minutes=interval)
    sessions = Session.query.filter(Session.last_request < time, Session.active==True).all()
    for session in sessions:
        session.active = False
        session.active_instance = None
        db.session.execute('DROP SCHEMA IF EXISTS %s CASCADE' % (session.schema))
        try:
            rmtree(session.working_path)
        except FileNotFoundError:
            pass
    db.session.commit()

@app.cli.command()
@click.argument("path")
def create_doc(path):
    """Write OpenAPI documentation to file.

    Arguments:
        path (str): Destination of documentation file (including filename).
    """
    import json
    from geometry_service import spec
    with open(path, 'w') as specfile:
        json.dump(spec.to_dict(), specfile)
    print("Wrote OpenAPI specification to {path}.".format(path=path))
