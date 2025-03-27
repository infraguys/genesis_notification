# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = []

    @property
    def migration_id(self):
        return "40a307b3-fdcc-46d8-bc81-1e2a53ac59e4"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            CREATE TYPE "enum_status_active" AS ENUM ('ACTIVE');
            """,
            """
            CREATE TYPE "enum_event_status" AS ENUM (
                'NEW',
                'IN_PROGRESS',
                'ACTIVE'
            );
            """,
            """
            CREATE TABLE "providers" (
                "uuid" CHAR(36) PRIMARY KEY,
                "name" VARCHAR(256) NOT NULL,
                "description" VARCHAR(256) NOT NULL,
                "status" enum_status_active NOT NULL DEFAULT 'ACTIVE',
                "project_id" CHAR(36) NOT NULL,
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "protocol" VARCHAR(1024) NOT NULL
            );
            """,
            """
            CREATE INDEX "providers_project_idx" ON "providers" (project_id);
            """,
            """
            CREATE INDEX "providers_name_idx" ON "providers" (name);
            """,
            """
            CREATE TABLE "event_types" (
                "uuid" CHAR(36) PRIMARY KEY,
                "name" VARCHAR(256) NOT NULL DEFAULT '',
                "description" VARCHAR(256) NOT NULL DEFAULT '',
                "status" enum_status_active NOT NULL DEFAULT 'ACTIVE',
                "project_id" CHAR(36),
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
            );
            """,
            """
            CREATE INDEX "event_types_project_idx" ON "event_types" (
                "project_id"
            );
            """,
            """
            CREATE TABLE "templates" (
                "uuid" CHAR(36) PRIMARY KEY,
                "name" VARCHAR(256) NOT NULL,
                "description" VARCHAR(256) NOT NULL,
                "status" enum_status_active NOT NULL DEFAULT 'ACTIVE',
                "project_id" CHAR(36) NOT NULL,
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "content" VARCHAR(10240) NOT NULL,
                "params" VARCHAR(4096) NOT NULL,
                "provider" CHAR(36) NOT NULL REFERENCES providers(uuid),
                "event_type" CHAR(36) NOT NULL REFERENCES event_types(uuid),
                "is_default" BOOLEAN NOT NULL DEFAULT FALSE
            );
            """,
            """
            CREATE INDEX "templates_project_idx" ON "templates" (
                "project_id"
            );
            """,
            """
            CREATE INDEX "templates_provider_idx" ON "templates" ("provider");
            """,
            """
            CREATE INDEX "templates_event_type_idx" ON "templates" (
                "event_type"
            );
            """,
            """
            CREATE TABLE "bindings" (
                "uuid" CHAR(36) PRIMARY KEY,
                "status" enum_status_active NOT NULL DEFAULT 'ACTIVE',
                "project_id" CHAR(36) NOT NULL,
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "user" CHAR(36) NOT NULL,
                "template" CHAR(36) NOT NULL REFERENCES templates(uuid),
                "event_type" CHAR(36) NOT NULL REFERENCES event_types(uuid)
            );
            """,
            """
            CREATE INDEX "bindings_user_idx" ON "bindings" ("user");
            """,
            """
            CREATE INDEX "bindings_template_idx" ON "bindings" ("template");
            """,
            """
            CREATE INDEX "bindings_event_type_idx" ON "bindings" (
                "event_type"
            );
            """,
            """
            CREATE TABLE "events" (
                "uuid" CHAR(36) PRIMARY KEY,
                "name" VARCHAR(256) NOT NULL DEFAULT '',
                "description" VARCHAR(256) NOT NULL DEFAULT '',
                "project_id" CHAR(36) NOT NULL,
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "status" enum_event_status NOT NULL DEFAULT 'NEW',
                "exchange" VARCHAR(1024) NOT NULL,
                "event_params" VARCHAR(4096) NOT NULL,
                "event_type" CHAR(36) NOT NULL REFERENCES event_types(uuid)
            );
            """,
            """
            CREATE INDEX "events_status_idx" ON "events" (status);
            """,
            """
            CREATE INDEX "events_event_type_idx" ON "events" (event_type);
            """,
            """
            CREATE TABLE "rendered_events" (
                "uuid" CHAR(36) PRIMARY KEY,
                "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                "status" enum_event_status NOT NULL DEFAULT 'IN_PROGRESS',
                "message" VARCHAR(10240) NOT NULL,
                "event_id" CHAR(36) NOT NULL,
                "provider" CHAR(36) NOT NULL REFERENCES providers(uuid),
                "user_context" VARCHAR(4096) NOT NULL
            );
            """,
            """
            CREATE INDEX "rendered_events_status_idx" ON "rendered_events" (
                "status"
            );
            """,
            """
            CREATE INDEX "rendered_events_provider_idx" ON "rendered_events" (
                "provider"
            );
            """,
            """
            CREATE OR REPLACE VIEW unprocessed_events AS
                SELECT
                    e.uuid AS uuid,
                    e.uuid AS event
                FROM
                    events e
                LEFT JOIN
                    rendered_events re ON (
                        re.event_id = e.uuid
                    )
                WHERE
                    re.uuid IS NULL;
            """,
            """
            CREATE OR REPLACE VIEW "incorrect_statuses" as
                SELECT
                    e."uuid",
                    e."uuid" as "event",
                    e."status" as "user_status",
                    re."status" as "system_status"
                FROM
                    "events" e
                left JOIN
                    "rendered_events" re ON (
                        re."event_id" = e."uuid"
                    )
                WHERE
                    re."uuid" is NOT NULL AND
                    e."status" != re."status"
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        views = ["unprocessed_events", "incorrect_statuses"]

        tables = [
            "rendered_events",
            "events",
            "bindings",
            "templates",
            "event_types",
            "providers",
        ]

        for view in views:
            self._delete_view_if_exists(session, view)

        for table in tables:
            self._delete_table_if_exists(session, table)

        session.execute('DROP TYPE IF EXISTS "enum_status_active" CASCADE;')
        session.execute('DROP TYPE IF EXISTS "enum_event_status" CASCADE;')


migration_step = MigrationStep()
