"""Config flow - exists solely to give real entity/service selectors for
the two fields that reference live HA data (notify service, AI Task
entity), since the App's own options schema has no entity type. Same
reasoning that justified the original companion integration, this time
for the right two fields instead of a watched_entities list that no
longer exists.

Uses Probatio for the form schema, as required by the Home Assistant
2026.11.0 form API.
"""

import probatio
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_NOTIFY_SERVICE, CONF_AI_TASK_ENTITY


def _schema(defaults: dict) -> probatio.Schema:
    notify_default = defaults.get(CONF_NOTIFY_SERVICE)
    ai_task_default = defaults.get(CONF_AI_TASK_ENTITY)

    notify_field: probatio.Required | probatio.Optional = (
        probatio.Required(CONF_NOTIFY_SERVICE, default=notify_default)
        if notify_default is not None
        else probatio.Required(CONF_NOTIFY_SERVICE)
    )
    ai_task_field: probatio.Required | probatio.Optional = (
        probatio.Required(CONF_AI_TASK_ENTITY, default=ai_task_default)
        if ai_task_default is not None
        else probatio.Required(CONF_AI_TASK_ENTITY)
    )

    return probatio.Schema(
        {
            notify_field: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="notify")
            ),
            ai_task_field: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="ai_task")
            ),
        }
    )


class AIAutonomyStewardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Abode AI Autonomy Steward Config", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return AIAutonomyStewardOptionsFlow(config_entry)


class AIAutonomyStewardOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(self.config_entry, data=user_input)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=_schema(dict(self.config_entry.data)))
