"""Initial migration.

Revision ID: 298821c225a6
Revises:
Create Date: 2021-02-22 12:33:27.951792

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '298821c225a6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE SCHEMA core')
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('session',
    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('token', sa.String(length=1023), nullable=False),
    sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_request', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('active', sa.BOOLEAN(), server_default=sa.text('true'), nullable=False),
    sa.Column('active_instance', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('schema', sa.String(length=127), nullable=True),
    sa.Column('working_path', sa.String(length=1023), nullable=True),
    sa.PrimaryKeyConstraint('uuid'),
    schema='core'
    )
    op.create_index('session_active_token_idx', 'session', ['token', 'active'], unique=True, schema='core', postgresql_where=sa.text('active'))
    op.create_index('session_inactive_token_idx', 'session', ['token', 'active'], unique=False, schema='core', postgresql_where=sa.text('NOT active'))
    op.create_table('datasets',
    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('session', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('table', sa.String(length=1023), nullable=False),
    sa.Column('filename', sa.String(length=1023), nullable=True),
    sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['session'], ['core.session.uuid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uuid'),
    schema='core'
    )
    op.create_table('actions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('session', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('action', sa.String(length=511), nullable=False),
    sa.Column('src_ds', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('result_ds', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('performed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['result_ds'], ['core.datasets.uuid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session'], ['core.session.uuid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['src_ds'], ['core.datasets.uuid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='core'
    )
    op.create_table('exports',
    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('dataset', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('driver', sa.String(length=127), nullable=False),
    sa.Column('status', postgresql.ENUM('completed', 'failed', 'processing', name='export_status_set', schema='core'), server_default='processing', nullable=False),
    sa.Column('file', sa.String(length=1023), nullable=True),
    sa.Column('output_path', sa.String(length=1023), nullable=True),
    sa.ForeignKeyConstraint(['dataset'], ['core.datasets.uuid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uuid'),
    schema='core'
    )
    op.create_index('exports_dataset_driver_idx', 'exports', ['dataset', 'driver'], unique=True, schema='core')
    op.create_table('queue',
    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('session', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ticket', sa.String(length=511), nullable=False),
    sa.Column('idempotent_key', sa.String(length=511), nullable=True),
    sa.Column('request', postgresql.ENUM('ingest', 'export', name='request_type_set', schema='core'), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('initiated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('execution_time', sa.Float(), nullable=True),
    sa.Column('completed', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('status', sa.BOOLEAN(), nullable=True),
    sa.Column('error_msg', sa.TEXT(), nullable=True),
    sa.Column('dataset', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('export', postgresql.UUID(as_uuid=True), nullable=True),
    sa.ForeignKeyConstraint(['dataset'], ['core.datasets.uuid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['export'], ['core.exports.uuid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session'], ['core.session.uuid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('uuid'),
    sa.UniqueConstraint('idempotent_key'),
    sa.UniqueConstraint('ticket'),
    schema='core'
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('queue', schema='core')
    op.drop_index('exports_dataset_driver_idx', table_name='exports', schema='core')
    op.drop_table('exports', schema='core')
    op.drop_table('actions', schema='core')
    op.drop_table('datasets', schema='core')
    op.drop_index('session_inactive_token_idx', table_name='session', schema='core')
    op.drop_index('session_active_token_idx', table_name='session', schema='core')
    op.drop_table('session', schema='core')
    # ### end Alembic commands ###
    op.execute('DROP SCHEMA core CASCADE')
