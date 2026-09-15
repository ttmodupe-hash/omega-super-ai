"""002_seed_sovereign_curriculum - seed template tracks for fresh clusters.

FIXED from the pasted version:
  - down_revision pointed at '001_initial_sovereign_tables' (rejected, never
    existed) -> alembic upgrade head would fail. Now chains to 0001_initial_schema.
  - Seed rows used student_id 00000000-...-000 which VIOLATES the FK to
    students(id). Now seeds a real system curriculum student and attaches the
    template tracks to it. Downgrade removes both.
  - lab_progress is per-student progress tracking, not a catalog: these rows
    are explicitly marked as templates via saved_state_metadata.is_template.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import uuid
import datetime

revision = "002_seed_sovereign_curriculum"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

SYSTEM_STUDENT_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "luqi-ai.system.curriculum"))


def upgrade() -> None:
    students = table(
        "students",
        column("id", sa.UUID()),
        column("email", sa.String()),
        column("full_name", sa.String()),
        column("country_code", sa.String()),
        column("tier", sa.String()),
        column("is_active", sa.Boolean()),
        column("created_at", sa.DateTime()),
    )
    op.bulk_insert(students, [{
        "id": SYSTEM_STUDENT_ID,
        "email": "system.curriculum@luqi-ai.local",
        "full_name": "Luqi-AI System Curriculum",
        "country_code": "ZAF",
        "tier": "PRIMARY", "is_active": True, "created_at": datetime.datetime(2026, 1, 1),
    }])

    lab_progress = table(
        "lab_progress",
        column("id", sa.UUID()),
        column("student_id", sa.UUID()),
        column("lab_track", sa.String()),
        column("completion_percentage", sa.Integer()),
        column("saved_state_metadata", sa.JSON()),
    )
    op.bulk_insert(lab_progress, [
        {
            "id": str(uuid.uuid4()),
            "student_id": SYSTEM_STUDENT_ID,
            "lab_track": "indigenous_botanic_synthesis",
            "completion_percentage": 0,
            "saved_state_metadata": {
                "is_template": True,
                "module_name": "Molecular Analysis of Sutherlandia frutescens",
                "methodology_focus": "Chemical rigor + Ubuntu empathy framing",
                "core_objective": "Isolating antiviral properties against tropical viral variants.",
            },
        },
        {
            "id": str(uuid.uuid4()),
            "student_id": SYSTEM_STUDENT_ID,
            "lab_track": "mechatronics_mineral_refinement",
            "completion_percentage": 0,
            "saved_state_metadata": {
                "is_template": True,
                "module_name": "Localized Lithium & Cobalt Processing Arm Automation",
                "methodology_focus": "High-precision kinematics + industrial scaling",
                "core_objective": "Programming robotic actuators to refine minerals on-continent.",
            },
        },
    ])


def downgrade() -> None:
    op.execute(f"DELETE FROM lab_progress WHERE student_id = '{SYSTEM_STUDENT_ID}';")
    op.execute(f"DELETE FROM students WHERE id = '{SYSTEM_STUDENT_ID}';")
