"""add phase 3 QA navigation entries

Revision ID: 0008_phase3_qa_navigation
Revises: 0007_merge_phase2_heads
Create Date: 2026-05-29
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0008_phase3_qa_navigation"
down_revision = "0007_merge_phase2_heads"
branch_labels = None
depends_on = None


FUNCTIONS = [
    ("qa", "智能问数", None, None, "chat", 60, None),
    ("qa_chat", "智能问数", "qa", "/qa/chat", "chat", 10, "qa.use"),
    ("qa_history", "问数历史", "qa", "/qa/history", "history", 20, "qa.use"),
]


def upgrade() -> None:
    bind = op.get_bind()
    function_ids: dict[str, str] = {}

    for code, name, parent_code, route_path, icon, sort_order, permission_code in FUNCTIONS:
        existing_id = bind.execute(
            sa.text("SELECT id FROM functions WHERE code = :code"),
            {"code": code},
        ).scalar_one_or_none()
        parent_id = function_ids.get(parent_code)

        if existing_id is None:
            existing_id = str(uuid4())
            bind.execute(
                sa.text(
                    """
                    INSERT INTO functions (
                        id, code, name, parent_id, route_path, icon, sort_order,
                        required_permission_code, status, is_system, created_at, updated_at
                    )
                    VALUES (
                        :id, :code, :name, :parent_id, :route_path, :icon, :sort_order,
                        :permission_code, 'active', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": existing_id,
                    "code": code,
                    "name": name,
                    "parent_id": parent_id,
                    "route_path": route_path,
                    "icon": icon,
                    "sort_order": sort_order,
                    "permission_code": permission_code,
                },
            )
        else:
            bind.execute(
                sa.text(
                    """
                    UPDATE functions
                    SET name = :name,
                        parent_id = :parent_id,
                        route_path = :route_path,
                        icon = :icon,
                        sort_order = :sort_order,
                        required_permission_code = :permission_code,
                        status = 'active',
                        is_system = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE code = :code
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "parent_id": parent_id,
                    "route_path": route_path,
                    "icon": icon,
                    "sort_order": sort_order,
                    "permission_code": permission_code,
                },
            )

        function_ids[code] = existing_id


def downgrade() -> None:
    op.execute("DELETE FROM functions WHERE code IN ('qa_chat', 'qa_history', 'qa')")
