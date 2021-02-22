from sqlalchemy.sql import expression, func
from sqlalchemy.dialects import postgresql
from geometry_service.database import db
import uuid

class Session(db.Model):
    """The Session Model.

    Extends:
        db.Model

    Attributes:
        uuid (uuid): The Primary Key.
        token (str): The token of the session.
        created (Datetime): Timestamp of the session creation.
        last_request (Datetime): Timestamp of the last request.
        active (bool): Whether the session is active or not.
        active_instance (str): The active dataset of the session.
        schema (str): The schema that session's datasets are stored.
        working_path (str): The working path for the session.
    """
    uuid = db.Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = db.Column(db.String(1023), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_request = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    active = db.Column(postgresql.BOOLEAN(), server_default=expression.true(), nullable=False)
    active_instance = db.Column(postgresql.UUID(as_uuid=True), nullable=True)
    schema = db.Column(db.String(127), nullable=True)
    working_path = db.Column(db.String(1023), nullable=True)
    __table_args__ = (
        db.Index('session_active_token_idx', token, active,
            unique=True,
            postgresql_where=(active)
        ),
        db.Index('session_inactive_token_idx', token, active,
            postgresql_where=(~active)
        ),
        {"schema": "core"}
    )

    def __iter__(self):
        for key in ['uuid', 'token', 'created', 'last_request', 'active', 'active_instance', 'schema', 'working_path']:
            yield (key, getattr(self, key))

    def get(self, token):
        session = self.query.filter_by(token=token, active=True).first()
        if session is None:
            return None
        session.last_request = func.now()
        db.session.add(session)
        db.session.commit()
        return dict(session)
