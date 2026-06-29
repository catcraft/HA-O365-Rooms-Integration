from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        RoomCurrentSensor(coordinator, entry),
        RoomNextSensor(coordinator, entry),
        RoomLastSensor(coordinator, entry),
    ])


class BaseRoomSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self.entry = entry
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = "mdi:calendar"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="O365 Room Calendar",
            manufacturer="PH Networks AG",
            model="Microsoft Graph Room Calendar",
        )

    def _get_event(self):
        data = self.coordinator.data or {}
        return data.get(self.key)


class RoomCurrentSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "current", "Current Meeting")

    @property
    def native_value(self):
        event = self._get_event()
        return event["subject"] if event else "Kein aktives Meeting"

    @property
    def extra_state_attributes(self):
        event = self._get_event()
        if not event:
            return {}
        return {
            "start": event["start_iso"],
            "end": event["end_iso"],
        }


class RoomNextSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "next", "Next Meeting")

    @property
    def native_value(self):
        event = self._get_event()
        return event["subject"] if event else None

    @property
    def extra_state_attributes(self):
        event = self._get_event()
        if not event:
            return {}
        return {
            "start": event["start_iso"],
            "end": event["end_iso"],
        }


class RoomLastSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "last", "Last Meeting")

    @property
    def native_value(self):
        event = self._get_event()
        return event["subject"] if event else None

    @property
    def extra_state_attributes(self):
        event = self._get_event()
        if not event:
            return {}
        return {
            "end": event["end_iso"],
        }