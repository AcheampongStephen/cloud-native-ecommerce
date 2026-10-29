"""Initial service-local storage; shared schema shape, separate databases."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "records",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("owner", sa.String(100), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_records_kind", "records", ["kind"])
    op.create_index("ix_records_owner", "records", ["owner"])
    op.create_table(
        "stock",
        sa.Column("product_id", sa.String(100), primary_key=True),
        sa.Column("available", sa.Integer(), nullable=False),
        sa.CheckConstraint("available >= 0", name="stock_nonnegative"),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_outbox_sent", "outbox", ["sent"])


def downgrade():
    op.drop_table("outbox")
    op.drop_table("stock")
    op.drop_table("records")
