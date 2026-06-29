from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        RoomUpdateButton(coordinator, entry)
    ])


class RoomUpdateButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = "Update Calendar"
        self._attr_unique_id = f"{entry.entry_id}_update_button"
        self._attr_icon = "mdi:refresh"

    async def async_press(self):
        await self.coordinator.async_request_refresh()