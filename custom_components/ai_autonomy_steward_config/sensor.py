"""Exposes the config-flow selections as sensor attributes, which the
App reads over the Supervisor-proxied Core API - same mechanism the
original continuous_autonomy_config integration used."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_NOTIFY_SERVICE, CONF_AI_TASK_ENTITY


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([AIAutonomyStewardConfigSensor(entry)])


class AIAutonomyStewardConfigSensor(SensorEntity):
    _attr_name = "AI Autonomy Steward Config"
    _attr_unique_id = f"{DOMAIN}_config"

    def __init__(self, entry: ConfigEntry):
        self._entry = entry

    @property
    def native_value(self):
        return "configured"

    @property
    def extra_state_attributes(self):
        return {
            CONF_NOTIFY_SERVICE: self._entry.data.get(CONF_NOTIFY_SERVICE),
            CONF_AI_TASK_ENTITY: self._entry.data.get(CONF_AI_TASK_ENTITY),
        }
