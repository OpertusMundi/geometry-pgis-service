from sqlalchemy import ForeignKey, event
from sqlalchemy.sql import expression
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from sqlalchemy.schema import DDL
from geometry_service.database import db
import uuid
from .session import Session

@event.listens_for(Session.active, 'set')
def set_datasets_deleted(target, value, oldvalue, initiator):
    """Tags the datasets as deleted.

    When a session becomes inactive, all the associated datasets should become inaccessible and tagged as 'deleted'. This function listens for events on the Session and performs this task.

    Decorators:
        event.listens_for
    """
    if not value and oldvalue:
        datasets = Datasets.query.filter_by(session=target.uuid, deleted=False).all()
        for dataset in datasets:
            dataset.deleted = True
        db.session.commit()


class Datasets(db.Model):
    """Datasets Model

    Extends:
        db.Model

    Attributes:
        uuid (UUID): Primary Key.
        label (str): The dataset label.
        session (UUID): Foreign Key to the session table.
        table (str): The table name containing the data of the dataset.
        filename (str): Full path of the file the dataset originated from; None if the dataset was not generated from file.
        created (datetime): Timestamp of the creation of the dataset.
        deleted (bool): Whether the dataset has been deleted or not.
        meta (dict): Metadata about the dataset.
    """
    __table_args__ = {"schema": "core"}
    uuid = db.Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = db.Column(db.String(255), nullable=False)
    session = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.session.uuid', ondelete="CASCADE"), nullable=False)
    table = db.Column(db.String(1023), nullable=False)
    filename = db.Column(db.String(1023), nullable=True)
    created = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted = db.Column(postgresql.BOOLEAN(), server_default=expression.false(), nullable=False)
    meta = db.Column(postgresql.JSONB(), nullable=False)

    def __iter__(self):
        for key in ['uuid', 'label', 'session', 'table', 'filename', 'created', 'deleted', 'meta']:
            yield (key, getattr(self, key))

    def get(self, **kwargs):
        dataset = self.query.filter_by(**kwargs).first()
        if dataset is None:
            return None
        return dict(dataset)
