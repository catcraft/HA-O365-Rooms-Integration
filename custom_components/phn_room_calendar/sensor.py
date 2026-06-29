from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ROOMS, CONF_UPDATE_INTERVAL
from .coordinator import GraphRoomCalendarCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = GraphRoomCalendarCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entities = [AllRoomsNextMeetingSensor(coordinator, entry)]
    for room in entry.data[CONF_ROOMS]:
        entities.append(RoomNextMeetingSensor(coordinator, entry, room))

    async_add_entities(entities)

class BaseRoomCalendarSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="O365 Rooms Calendar",
            manufacturer="PH Networks AG",
            model="Microsoft Graph Room Calendar",
        )

class AllRoomsNextMeetingSensor(BaseRoomCalendarSensor):
    _attr_name = "All Rooms Next Meeting"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_all_rooms_next_meeting"

    @property
    def native_value(self):
        next_event = self.coordinator.data.get("all_next") if self.coordinator.data else None
        return next_event["subject"] if next_event else "No upcoming meeting"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        next_event = data.get("all_next")
        return {
            "next": next_event,
            "events": data.get("all_events", []),
            "last_update": data.get("last_update"),
        }

class RoomNextMeetingSensor(BaseRoomCalendarSensor):
    _attr_icon = "mdi:door-open"

    def __init__(self, coordinator, entry: ConfigEntry, room: str):
        super().__init__(coordinator, entry)
        self.room = room
        self._attr_unique_id = f"{entry.entry_id}_{room}_next_meeting"
        self._attr_name = f"{room} Next Meeting"

    @property
    def native_value(self):
        room_data = (self.coordinator.data or {}).get("rooms", {}).get(self.room, {})
        next_event = room_data.get("next")
        if room_data.get("occupied") and next_event:
            return f"Occupied: {next_event['subject']}"
        return next_event["subject"] if next_event else "Free"

    @property
    def extra_state_attributes(self):
        room_data = (self.coordinator.data or {}).get("rooms", {}).get(self.room, {})
        next_event = room_data.get("next")
        return {
            "room": self.room,
            "occupied": room_data.get("occupied", False),
            "next": next_event,
            "events": room_data.get("events", []),
            "start": next_event.get("start_iso") if next_event else None,
            "end": next_event.get("end_iso") if next_event else None,
            "start_time": next_event.get("start_time") if next_event else None,
            "end_time": next_event.get("end_time") if next_event else None,
        }
