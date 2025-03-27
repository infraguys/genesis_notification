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

import logging

from gcl_looper.services import basic
from restalchemy.common import contexts
from restalchemy.dm import filters
import jinja2

from genesis_notification.dm import models


LOG = logging.getLogger(__name__)


class EventBuilderAgent(basic.BasicService):

    def __init__(self, iam_client, butch_size=100, **kwargs):
        self._iam_client = iam_client
        self._butch_size = butch_size
        super().__init__(**kwargs)

    def _setup(self):
        pass

    def _get_user_context(self, event):
        return self._iam_client.get_user(event.exchange.user_id)

    def _build_event_message(self, event, provider):
        template = models.Template.objects.get_one(
            filters={
                "event_type": filters.EQ(event.event_type),
                "provider": filters.EQ(provider),
            }
        )
        return jinja2.Template(template.content).render(**event.event_params)

    def _get_providers(self, event, user_context):
        templates = models.Template.objects.get_all(
            filters={
                "event_type": filters.EQ(event.event_type),
                "is_default": filters.EQ(True),
            }
        )
        return [template.provider for template in templates]

    def _process_user_event(self, event):
        LOG.info("Processing event: %s", event.uuid)
        user_context = self._get_user_context(event)
        providers = self._get_providers(event, user_context)
        for provider in providers:
            rendered_event = models.RenderedEvent(
                event_id=event.uuid,
                message=self._build_event_message(event, provider),
                provider=provider,
                user_context=user_context,
            )
            rendered_event.insert()

    def _process_unprocessed_events(self):
        unprocessed_events = models.UnprocessedEvent.objects.get_all(
            limit=self._butch_size,
        )
        for e in unprocessed_events:
            if isinstance(e.event.exchange, models.UserExchange):
                self._process_user_event(e.event)
            else:
                raise NotImplementedError(
                    f"{e.event.exchange} is not implemented"
                )

    def _sync_event_statuses(self):
        for item in models.IncorrectStatuses.objects.get_all(
            limit=self._butch_size,
        ):
            LOG.info("Syncing item status: %r", item)
            event = item.event
            event.status = item.system_status
            event.update()

    def _iteration(self):
        ctx = contexts.Context()
        with ctx.session_manager():
            self._process_unprocessed_events()
            self._sync_event_statuses()
