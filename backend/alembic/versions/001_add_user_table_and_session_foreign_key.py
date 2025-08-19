"""Add User table and Session user_id foreign key

Revision ID: 001
Revises:
Create Date: 2025-08-19 17:00:00.000000

This migration:
1. Creates the users table for OAuth authentication
2. Adds user_id foreign key to sessions table
3. Provides safe rollback with data preservation
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add User table and update Session with user_id FK."""

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False, server_default="google"),
        sa.Column("provider_sub", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="author"),
        sa.Column("monthly_budget_usd", sa.Numeric(10, 2), server_default="100.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for users table
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_provider_sub", "users", ["provider_sub"], unique=True)

    # Check if sessions table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "sessions" in inspector.get_table_names():
        # Check if user_id column already exists
        columns = [col["name"] for col in inspector.get_columns("sessions")]

        if "user_id" not in columns:
            # Add user_id column to sessions table (nullable initially for existing data)
            op.add_column(
                "sessions", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
            )

            # Create a default user for existing sessions (optional)
            # This ensures existing sessions continue to work
            result = conn.execute(
                sa.text(
                    """
                INSERT INTO users (id, email, name, provider, provider_sub, role)
                VALUES (
                    '00000000-0000-0000-0000-000000000000'::uuid,
                    'legacy@sopher.ai',
                    'Legacy User',
                    'system',
                    'legacy',
                    'author'
                )
                ON CONFLICT (provider_sub) DO NOTHING
                RETURNING id
            """
                )
            )

            # Update existing sessions to use the legacy user
            if result.rowcount > 0:
                op.execute(
                    """
                    UPDATE sessions
                    SET user_id = '00000000-0000-0000-0000-000000000000'::uuid
                    WHERE user_id IS NULL
                """
                )

            # Now make user_id NOT NULL after populating it
            op.alter_column("sessions", "user_id", nullable=False)

            # Add foreign key constraint
            op.create_foreign_key(
                "fk_sessions_user_id", "sessions", "users", ["user_id"], ["id"], ondelete="CASCADE"
            )

            # Create index on user_id for performance
            op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    """Rollback migration: Remove User table and Session user_id FK."""

    # Check if sessions table exists before trying to modify it
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "sessions" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("sessions")]

        if "user_id" in columns:
            # Drop foreign key constraint
            op.drop_constraint("fk_sessions_user_id", "sessions", type_="foreignkey")

            # Drop index
            op.drop_index("ix_sessions_user_id", "sessions")

            # Drop the column
            op.drop_column("sessions", "user_id")

    # Drop users table indexes
    op.drop_index("ix_users_provider_sub", "users")
    op.drop_index("ix_users_email", "users")

    # Drop users table
    op.drop_table("users")
