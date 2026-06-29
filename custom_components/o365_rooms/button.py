from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RoomUpdateButton(coordinator, entry),
        ]
    )


class RoomUpdateButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Update Calendar"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)

        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_update_calendar"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="O365 Room Calendar",
            manufacturer="PH Networks AG",
            model="Microsoft Graph Room Calendar",
        )

    async def async_press(self):
        await self.coordinator.async_request_refresh()