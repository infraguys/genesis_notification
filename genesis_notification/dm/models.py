#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
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

from email.mime import text
from email.mime import multipart
import smtplib

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from restalchemy.storage.sql import orm

from genesis_notification.common import constants as c


class ModelWithAlwaysActiveStatus(models.Model):

    STATUS = c.AlwaysActiveStatus

    status = properties.property(
        types.Enum([s.value for s in c.AlwaysActiveStatus]),
        default=STATUS.ACTIVE.value,
    )


class SimpleSmtpProtocol(types_dynamic.AbstractKindModel):
    KIND = "SimpleSMTP"

    host = properties.property(
        types.String(min_length=1, max_length=128),
        required=True,
    )
    port = properties.property(
        types.Integer(min_value=1, max_value=65535),
        required=True,
    )
    noreply_email_address = properties.property(
        types.Email(),
        required=True,
    )

    def _parse_message(self, message):
        subject = ""
        body = message
        parts = message.split("\n", 2)
        if len(parts) > 2 and parts[1] == "":
            subject = parts[0]
            body = parts[2]
        return subject, body

    def _build_message(self, message, user_context):
        subject, body = self._parse_message(message)
        msg = multipart.MIMEMultipart("alternative")
        msg["From"] = self.noreply_email_address
        msg["To"] = user_context["email"]
        msg["Subject"] = subject
        msg.attach(text.MIMEText(body, "html", "utf-8"))
        return msg

    def send(self, message, user_context):
        msg = self._build_message(message, user_context)
        with smtplib.SMTP(self.host, self.port) as smtp:
            return smtp.sendmail(
                from_addr=self.noreply_email_address,
                to_addrs=user_context["email"],
                msg=msg.as_string(),
            )


class Provider(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
    ModelWithAlwaysActiveStatus,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "providers"
    __jsonfields__ = ["protocol"]

    protocol = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(SimpleSmtpProtocol),
        ),
        required=True,
    )

    def send(self, message, user_context):
        return self.protocol.send(
            message=message,
            user_context=user_context,
        )


class EventType(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    ModelWithAlwaysActiveStatus,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "event_types"


class Template(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
    ModelWithAlwaysActiveStatus,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "templates"
    __jsonfields__ = ["params"]

    content = properties.property(
        types.String(max_length=10240),
        required=True,
    )
    params = properties.property(
        types.Dict(),
        required=True,
    )
    provider = relationships.relationship(
        Provider,
        required=True,
        prefetch=True,
    )
    event_type = relationships.relationship(EventType, required=True)
    is_default = properties.property(
        types.Boolean(),
        default=False,
    )


class UserExchange(types_dynamic.AbstractKindModel):
    KIND = "User"

    user_id = properties.property(
        types.UUID(),
        required=True,
    )


class ProjectExchange(types_dynamic.AbstractKindModel):
    KIND = "Project"

    project_id = properties.property(
        types.UUID(),
        required=True,
    )


class SystemExchange(types_dynamic.AbstractKindModel):
    KIND = "System"


class Binding(
    models.ModelWithUUID,
    models.ModelWithProject,
    ModelWithAlwaysActiveStatus,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    user = properties.property(
        types.UUID(),
        required=True,
    )
    template = relationships.relationship(
        Template,
        required=True,
    )
    event_type = relationships.relationship(
        EventType,
        required=True,
    )


class Event(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "events"
    __jsonfields__ = ["exchange", "event_params"]

    STATUS = c.EventStatus

    status = properties.property(
        types.Enum([s.value for s in STATUS]),
        default=STATUS.NEW.value,
    )
    exchange = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(UserExchange),
            types_dynamic.KindModelType(ProjectExchange),
            types_dynamic.KindModelType(SystemExchange),
        ),
        required=True,
    )
    event_params = properties.property(
        types.Dict(),
        required=True,
    )
    event_type = relationships.relationship(
        EventType,
        required=True,
    )


class RenderedEvent(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "rendered_events"
    __jsonfields__ = ["user_context"]
    STATUS = c.EventStatus

    status = properties.property(
        types.Enum([s.value for s in STATUS]),
        default=STATUS.IN_PROGRESS.value,
    )
    message = properties.property(
        types.String(max_length=10240),
        required=True,
    )
    event_id = properties.property(
        types.UUID(),
        required=True,
    )
    provider = relationships.relationship(
        Provider,
        required=True,
        prefetch=True,
    )
    user_context = properties.property(
        types.Dict(),
        required=True,
    )

    def send(self):
        self.provider.send(
            message=self.message,
            user_context=self.user_context,
        )


class UnprocessedEvent(
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    __tablename__ = "unprocessed_events"
    event = relationships.relationship(
        Event,
        required=True,
        prefetch=True,
    )


class IncorrectStatuses(
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    __tablename__ = "incorrect_statuses"

    STATUS = c.EventStatus

    event = relationships.relationship(
        Event,
        required=True,
        prefetch=True,
    )
    user_status = properties.property(
        types.Enum([s.value for s in STATUS]),
        required=True,
    )
    system_status = properties.property(
        types.Enum([s.value for s in STATUS]),
        required=True,
    )
