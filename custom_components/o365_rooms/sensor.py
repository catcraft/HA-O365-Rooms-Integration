from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RoomCalendarSensor(coordinator, entry)])


class RoomCalendarSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)

        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_meeting"
        self._attr_name = "Next Meeting"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="O365 Room Calendar",
            manufacturer="PH Networks AG",
            model="Microsoft Graph Room Calendar",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        next_event = data.get("next")

        if not data:
            _LOGGER.warning("Coordinator data is empty")
            return "No data"

        return next_event["subject"] if next_event else "No upcoming meeting"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}

        next_event = data.get("next")
        last_event = data.get("last")

        return {
            "room": data.get("room"),
            "occupied": data.get("occupied", False),

            "next": next_event,
            "next_subject": next_event.get("subject") if next_event else None,
            "next_date": next_event.get("date") if next_event else None,
            "next_start": next_event.get("start_time") if next_event else None,
            "next_end": next_event.get("end_time") if next_event else None,
            "next_start_iso": next_event.get("start_iso") if next_event else None,
            "next_end_iso": next_event.get("end_iso") if next_event else None,

            "last": last_event,
            "last_subject": last_event.get("subject") if last_event else None,
            "last_date": last_event.get("date") if last_event else None,
            "last_start": last_event.get("start_time") if last_event else None,
            "last_end": last_event.get("end_time") if last_event else None,
            "last_start_iso": last_event.get("start_iso") if last_event else None,
            "last_end_iso": last_event.get("end_iso") if last_event else None,

            "events": data.get("events", []),
            "past_events": data.get("past_events", []),
            "last_update": data.get("last_update"),
        }