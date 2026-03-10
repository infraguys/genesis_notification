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
import datetime

from restalchemy.api import controllers as ra_controllers
from restalchemy.api import resources

from genesis_notification.common import constants as c
from genesis_notification.dm import models
from genesis_notification.user_api.api import versions


class RootController(ra_controllers.Controller):
    """Controller for / endpoint"""

    def filter(self, filters):
        return (versions.API_VERSION_1_0,)


class ApiEndpointController(ra_controllers.RoutesListController):
    """Controller for /v1/ endpoint"""

    __TARGET_PATH__ = "/v1/"


class ProviderController(ra_controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.Provider, convert_underscore=False
    )


class TemplateController(ra_controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.Template, convert_underscore=False
    )


class EventTypeController(ra_controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.EventType, convert_underscore=False
    )


class EventController(ra_controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.Event, convert_underscore=False
    )


class InstallationController(ra_controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.Installation,
        convert_underscore=False,
    )

    def _update_existing(self, existing, resource):
        existing.push_token = resource["push_token"]
        existing.platform = resource["platform"]

        existing.app_version = resource.get("app_version", "")
        existing.os_version = resource.get("os_version", "")
        existing.device_model = resource.get("device_model", "")

        existing.status = c.AlwaysActiveStatus.ACTIVE.value
        existing.user_id = resource.get("user_id", "")

        existing.save()

        return existing

    def create(self, **kwargs):
        installation_id = kwargs.get("installation_id")

        existing = models.Installation.objects.get_one(
            filters={
                "installation_id": installation_id,
            }
        )

        if existing:
            return self._update_existing(existing, kwargs)

        return super().create(**kwargs)
