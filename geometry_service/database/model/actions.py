from sqlalchemy import ForeignKey
from sqlalchemy.sql import expression
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from geometry_service.database import db
import uuid

class Actions(db.Model):
    """Actions Model

    Extends:
        db.Model

    Attributes:
        id (int): Primary Key
        session (UUID): Foreign Key to session table
        action (str): The action applied
        src_ds (UUID): Foreign Key to the datasets table; the source dataset.
        result_ds (UUID): Foreign Key to the datasets table; the resulted dataset.
        performed (datetime): Timestamp of the action.
    """
    __table_args__ = {"schema": "core"}
    id = db.Column(db.BigInteger(), primary_key=True)
    session = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.session.uuid', ondelete="CASCADE"), nullable=False)
    action = db.Column(db.String(511), nullable=False)
    src_ds = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.datasets.uuid', ondelete="CASCADE"), nullable=False)
    result_ds = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.datasets.uuid', ondelete="CASCADE"), nullable=False)
    performed = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __iter__(self):
        for key in ['id', 'session', 'action', 'src_ds', 'result_ds', 'performed']:
            yield (key, getattr(self, key))
