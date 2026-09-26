from django.db import migrations


SUBJECT_ID_MAP = {
    2: 7,   # MATHEMATICS
    3: 3,   # ENGLISH
    4: 6,   # KISWAHILI
    5: 11,  # SOCIAL STUDIES
    6: 10,  # SCIENCE
    7: 5,   # INTEGRATED SCIENCE
    8: 1,   # AGRICULTURE
    9: 4,   # FRENCH
    10: 2,  # COMPUTER
    11: 9,  # RELIGIOUS EDUCATION
    12: 8,  # PRETECHNICAL STUDIES
}


def repair_weekly_report_subject_fk(apps, schema_editor):
    connection = schema_editor.connection

    if connection.vendor != "sqlite":
        return

    table = "weekly_reports_weeklyassessmentreport"

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
            AND name = '{table}'
            """
        )

        row = cursor.fetchone()

        if not row or not row[0]:
            return

        if '"scheduling_subject"' not in row[0]:
            return

        print(
            "Repairing WeeklyAssessmentReport.subject_id: "
            "scheduling_subject -> timetable_timetablesubject"
        )

        cursor.execute(
            f"""
            SELECT DISTINCT subject_id
            FROM "{table}"
            ORDER BY subject_id
            """
        )

        old_subject_ids = {
            int(row[0])
            for row in cursor.fetchall()
        }

        missing = sorted(
            old_subject_ids.difference(SUBJECT_ID_MAP)
        )

        if missing:
            raise RuntimeError(
                "Cannot repair weekly assessment subjects. "
                f"Unmapped old subject IDs: {missing}"
            )

        cursor.execute(
            f"""
            CREATE TABLE "{table}__new" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "class_name" varchar(100) NOT NULL,
                "stream" varchar(100) NOT NULL,
                "week_start" date NOT NULL,
                "week_end" date NOT NULL,
                "week_number" smallint unsigned NOT NULL
                    CHECK ("week_number" >= 0),
                "score" decimal NULL,
                "max_score" decimal NOT NULL,
                "teacher_report" text NOT NULL,
                "is_published" bool NOT NULL,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL,
                "created_by_id" integer NULL
                    REFERENCES "auth_user" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "student_id" bigint NOT NULL
                    REFERENCES "students_student" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "subject_id" bigint NOT NULL
                    REFERENCES "timetable_timetablesubject" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "updated_by_id" integer NULL
                    REFERENCES "auth_user" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "week_id" bigint NULL
                    REFERENCES "weekly_reports_weeklyassessmentweek" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "unique_student_subject_weekly_report"
                    UNIQUE (
                        "student_id",
                        "subject_id",
                        "week_start",
                        "week_end"
                    )
            )
            """
        )

        case_parts = " ".join(
            f"WHEN {old_id} THEN {new_id}"
            for old_id, new_id in SUBJECT_ID_MAP.items()
        )

        cursor.execute(
            f"""
            INSERT INTO "{table}__new" (
                "id",
                "class_name",
                "stream",
                "week_start",
                "week_end",
                "week_number",
                "score",
                "max_score",
                "teacher_report",
                "is_published",
                "created_at",
                "updated_at",
                "created_by_id",
                "student_id",
                "subject_id",
                "updated_by_id",
                "week_id"
            )
            SELECT
                "id",
                "class_name",
                "stream",
                "week_start",
                "week_end",
                "week_number",
                "score",
                "max_score",
                "teacher_report",
                "is_published",
                "created_at",
                "updated_at",
                "created_by_id",
                "student_id",
                CASE "subject_id"
                    {case_parts}
                    ELSE NULL
                END,
                "updated_by_id",
                "week_id"
            FROM "{table}"
            """
        )

        cursor.execute(
            f'DROP TABLE "{table}"'
        )

        cursor.execute(
            f"""
            ALTER TABLE "{table}__new"
            RENAME TO "{table}"
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_student_5a127e_idx"
            ON "{table}" ("student_id", "week_start")
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_subject_eb6361_idx"
            ON "{table}" ("subject_id", "week_start")
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_class_n_717d11_idx"
            ON "{table}" ("class_name", "week_start")
            """
        )

        print(
            f"Repaired {len(old_subject_ids)} old subject IDs."
        )


def reverse_repair(apps, schema_editor):
    connection = schema_editor.connection

    if connection.vendor != "sqlite":
        return

    table = "weekly_reports_weeklyassessmentreport"

    reverse_map = {
        new_id: old_id
        for old_id, new_id in SUBJECT_ID_MAP.items()
    }

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE "{table}__old" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "class_name" varchar(100) NOT NULL,
                "stream" varchar(100) NOT NULL,
                "week_start" date NOT NULL,
                "week_end" date NOT NULL,
                "week_number" smallint unsigned NOT NULL
                    CHECK ("week_number" >= 0),
                "score" decimal NULL,
                "max_score" decimal NOT NULL,
                "teacher_report" text NOT NULL,
                "is_published" bool NOT NULL,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL,
                "created_by_id" integer NULL
                    REFERENCES "auth_user" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "student_id" bigint NOT NULL
                    REFERENCES "students_student" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "subject_id" bigint NOT NULL
                    REFERENCES "scheduling_subject" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "updated_by_id" integer NULL
                    REFERENCES "auth_user" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "week_id" bigint NULL
                    REFERENCES "weekly_reports_weeklyassessmentweek" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "unique_student_subject_weekly_report"
                    UNIQUE (
                        "student_id",
                        "subject_id",
                        "week_start",
                        "week_end"
                    )
            )
            """
        )

        case_parts = " ".join(
            f"WHEN {new_id} THEN {old_id}"
            for new_id, old_id in reverse_map.items()
        )

        cursor.execute(
            f"""
            INSERT INTO "{table}__old" (
                "id",
                "class_name",
                "stream",
                "week_start",
                "week_end",
                "week_number",
                "score",
                "max_score",
                "teacher_report",
                "is_published",
                "created_at",
                "updated_at",
                "created_by_id",
                "student_id",
                "subject_id",
                "updated_by_id",
                "week_id"
            )
            SELECT
                "id",
                "class_name",
                "stream",
                "week_start",
                "week_end",
                "week_number",
                "score",
                "max_score",
                "teacher_report",
                "is_published",
                "created_at",
                "updated_at",
                "created_by_id",
                "student_id",
                CASE "subject_id"
                    {case_parts}
                    ELSE "subject_id"
                END,
                "updated_by_id",
                "week_id"
            FROM "{table}"
            """
        )

        cursor.execute(
            f'DROP TABLE "{table}"'
        )

        cursor.execute(
            f"""
            ALTER TABLE "{table}__old"
            RENAME TO "{table}"
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_student_5a127e_idx"
            ON "{table}" ("student_id", "week_start")
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_subject_eb6361_idx"
            ON "{table}" ("subject_id", "week_start")
            """
        )

        cursor.execute(
            f"""
            CREATE INDEX "weekly_repo_class_n_717d11_idx"
            ON "{table}" ("class_name", "week_start")
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "weekly_reports",
            "0002_weeklyassessmentweek_weeklyassessmentreport_week_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            repair_weekly_report_subject_fk,
            reverse_code=reverse_repair,
        ),
    ]
