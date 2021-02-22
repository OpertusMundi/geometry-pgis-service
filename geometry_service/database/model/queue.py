from sqlalchemy import ForeignKey, event
from sqlalchemy.sql import expression
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from sqlalchemy.schema import DDL
from geometry_service.database import db
import uuid
from hashlib import md5

class Queue(db.Model):
    """Queue Model

    Extends:
        db.Model

    Attributes:
        uuid (uuid): Primary Key.
        session (uuid): The Foreign Key to the sessions table.
        ticket (str): The ticket assigned to the request.
        idempotent_key (str): An idempotency key sent along with the request.
        request (str): The request type.
        label (str): The label of the dataset.
        initiated (datetime): The timestamp of the request.
        execution_time (float): The execution time in seconds.
        completed (bool): Whether the process has been completed.
        status (bool): The status of the process.
        error_msg (str): The error message in case of failure.
        dataset (uuid): The Foreign Key to the datasets table.
        export (uuid): The Foreign Key to the exports table.
    """
    __table_args__ = {"schema": "core"}
    uuid = db.Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.session.uuid', ondelete="CASCADE"), nullable=False)
    ticket = db.Column(db.String(511), default=lambda: md5(str(uuid.uuid4()).encode()).hexdigest(), nullable=False, unique=True)
    idempotent_key = db.Column(db.String(511), nullable=True, unique=True)
    request = db.Column(postgresql.ENUM('ingest', 'export', name='request_type_set', schema='core'), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    initiated = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    execution_time = db.Column(db.Float(), nullable=True)
    completed = db.Column(postgresql.BOOLEAN(), server_default=expression.false(), nullable=False)
    status = db.Column(postgresql.BOOLEAN(), nullable=True)
    error_msg = db.Column(postgresql.TEXT(), nullable=True)
    dataset = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.datasets.uuid', ondelete="CASCADE"), nullable=True)
    export = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.exports.uuid', ondelete="CASCADE"), nullable=True)

    def __iter__(self):
        for key in ['uuid', 'ticket', 'idempotent_key', 'request', 'initiated', 'execution_time', 'completed', 'status', 'error_msg', 'dataset', 'export']:
            yield (key, getattr(self, key))

    def get(self, **kwargs):
        queue = self.query.filter_by(**kwargs).first()
        if queue is None:
            return None
        return dict(queue)