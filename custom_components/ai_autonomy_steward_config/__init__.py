"""AI Autonomy Steward Config - companion integration.

Exists solely because the App's own options schema has no entity/service
selector type. This integration's config flow provides real EntitySelector
pickers for notify_service and the AI Task entity, and exposes the result
as sensor.ai_autonomy_steward_config's attributes for the App to read.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
