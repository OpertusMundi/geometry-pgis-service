from sqlalchemy import ForeignKey, event
from sqlalchemy.sql import expression
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from sqlalchemy.schema import DDL
from geometry_service.database import db
import uuid

class Exports(db.Model):
    """Exports Model

    Extends:
        db.Model

    Attributes:
        uuid (uuid): The Primary Key.
        dataset (uuid): The Foreign Key to the datasets table.
        driver (str): The driver used to export the file.
        status (str): The status of the export, one of 'completed', 'failed', 'processing'.
        file (str): The exported file path.
        output_path (str): The path of the file in output directory (if copied).
    """
    uuid = db.Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset = db.Column(postgresql.UUID(as_uuid=True), ForeignKey('core.datasets.uuid', ondelete="CASCADE"), nullable=False)
    driver = db.Column(db.String(127), nullable=False)
    status = db.Column(postgresql.ENUM('completed', 'failed', 'processing', name='export_status_set', schema='core'), server_default='processing', nullable=False)
    file = db.Column(db.String(1023), nullable=True)
    output_path = db.Column(db.String(1023), nullable=True)

    __table_args__ = (
        db.Index('exports_dataset_driver_idx', dataset, driver, unique=True),
        {"schema": "core"}
    )

    def __iter__(self):
        for key in ['uuid', 'dataset', 'driver', 'status', 'file', 'error_msg']:
            yield (key, getattr(self, key))

    def get(self, **kwargs):
        export = self.query.filter_by(**kwargs).first()
        if export is None:
            return None
        return dict(export)