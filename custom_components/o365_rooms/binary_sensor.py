from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


LIVE_UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RoomOccupiedBinarySensor(coordinator, entry),
        ]
    )


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _get_current_event(events: list[dict], tz):
    now = datetime.now(tz)

    sorted_events = sorted(events, key=lambda event: event["start_iso"])

    current_event = None

    for event in sorted_events:
        start = _parse_iso(event["start_iso"])
        end = _parse_iso(event["end_iso"])

        if start <= now < end:
            current_event = event

    return current_event


class RoomOccupiedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Room Occupied"
    _attr_icon = "mdi:calendar-check"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)

        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_room_occupied"

        self._unsub_timer = None

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="O365 Room Calendar",
            manufacturer="PH Networks AG",
            model="Microsoft Graph Room Calendar",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._handle_timer,
            LIVE_UPDATE_INTERVAL,
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

        await super().async_will_remove_from_hass()

    @callback
    def _handle_timer(self, now):
        self.async_write_ha_state()

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        events = data.get("events", [])

        return _get_current_event(events, self.coordinator.tz) is not None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        events = data.get("events", [])

        current_event = _get_current_event(events, self.coordinator.tz)

        if not current_event:
            return {
                "current_subject": None,
                "graph_last_update": data.get("graph_last_update"),
            }

        return {
            "current_subject": current_event["subject"],
            "current_start": current_event["start_iso"],
            "current_end": current_event["end_iso"],
            "graph_last_update": data.get("graph_last_update"),
        }