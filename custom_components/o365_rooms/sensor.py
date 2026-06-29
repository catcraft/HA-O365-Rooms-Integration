from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
            RoomCurrentSensor(coordinator, entry),
            RoomNextSensor(coordinator, entry),
            RoomLastSensor(coordinator, entry),
            RoomNextStartTimeSensor(coordinator, entry),
            RoomNextEndTimeSensor(coordinator, entry),
            RoomNextStartsInSensor(coordinator, entry),
        ]
    )


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _split_events(events: list[dict], tz):
    now = datetime.now(tz)

    current_event = None
    future_events = []
    past_events = []

    sorted_events = sorted(events, key=lambda event: event["start_iso"])

    for event in sorted_events:
        start = _parse_iso(event["start_iso"])
        end = _parse_iso(event["end_iso"])

        if start <= now < end:
            current_event = event
        elif start > now:
            future_events.append(event)
        elif end <= now:
            past_events.append(event)

    future_events.sort(key=lambda event: event["start_iso"])
    past_events.sort(key=lambda event: event["end_iso"])

    next_event = future_events[0] if future_events else None
    last_event = past_events[-1] if past_events else None

    return current_event, next_event, last_event


def _seconds_until(event: dict | None, tz) -> int | None:
    if not event:
        return None

    now = datetime.now(tz)
    start = _parse_iso(event["start_iso"])

    seconds = int((start - now).total_seconds())

    return max(seconds, 0)


def _minutes_until(event: dict | None, tz) -> int | None:
    seconds = _seconds_until(event, tz)

    if seconds is None:
        return None

    return seconds // 60


class BaseRoomSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry, key: str, name: str):
        super().__init__(coordinator)

        self.entry = entry
        self.key = key

        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = "mdi:calendar-clock"

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

    def _get_events(self) -> list[dict]:
        data = self.coordinator.data or {}
        return data.get("events", [])

    def _get_live_events(self):
        return _split_events(self._get_events(), self.coordinator.tz)

    @property
    def available(self):
        return self.coordinator.last_update_success


class RoomCurrentSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "current_meeting", "Current Meeting")

    @property
    def native_value(self):
        current_event, _, _ = self._get_live_events()

        if not current_event:
            return "Kein aktives Meeting"

        return current_event["subject"]

    @property
    def extra_state_attributes(self):
        current_event, _, _ = self._get_live_events()
        data = self.coordinator.data or {}

        if not current_event:
            return {
                "occupied": False,
                "graph_last_update": data.get("graph_last_update"),
            }

        return {
            "occupied": True,
            "subject": current_event["subject"],
            "start": current_event["start_iso"],
            "end": current_event["end_iso"],
            "date": current_event["date"],
            "start_time": current_event["start_time"],
            "end_time": current_event["end_time"],
            "graph_last_update": data.get("graph_last_update"),
        }


class RoomNextSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "next_meeting", "Next Meeting")

    @property
    def native_value(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return None

        return next_event["subject"]

    @property
    def extra_state_attributes(self):
        _, next_event, _ = self._get_live_events()
        data = self.coordinator.data or {}

        if not next_event:
            return {
                "graph_last_update": data.get("graph_last_update"),
            }

        return {
            "subject": next_event["subject"],
            "start": next_event["start_iso"],
            "end": next_event["end_iso"],
            "date": next_event["date"],
            "start_time": next_event["start_time"],
            "end_time": next_event["end_time"],
            "seconds_until_start": _seconds_until(next_event, self.coordinator.tz),
            "minutes_until_start": _minutes_until(next_event, self.coordinator.tz),
            "graph_last_update": data.get("graph_last_update"),
        }


class RoomLastSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "last_meeting", "Last Meeting")

    @property
    def native_value(self):
        _, _, last_event = self._get_live_events()

        if not last_event:
            return None

        return last_event["subject"]

    @property
    def extra_state_attributes(self):
        _, _, last_event = self._get_live_events()
        data = self.coordinator.data or {}

        if not last_event:
            return {
                "graph_last_update": data.get("graph_last_update"),
            }

        return {
            "subject": last_event["subject"],
            "start": last_event["start_iso"],
            "end": last_event["end_iso"],
            "date": last_event["date"],
            "start_time": last_event["start_time"],
            "end_time": last_event["end_time"],
            "graph_last_update": data.get("graph_last_update"),
        }


class RoomNextStartTimeSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(
            coordinator,
            entry,
            "next_meeting_start_time",
            "Next Meeting Start Time",
        )
        self._attr_icon = "mdi:clock-start"

    @property
    def native_value(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return None

        return next_event["start_time"]

    @property
    def extra_state_attributes(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return {}

        return {
            "start": next_event["start_iso"],
            "subject": next_event["subject"],
        }


class RoomNextEndTimeSensor(BaseRoomSensor):
    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(
            coordinator,
            entry,
            "next_meeting_end_time",
            "Next Meeting End Time",
        )
        self._attr_icon = "mdi:clock-end"

    @property
    def native_value(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return None

        return next_event["end_time"]

    @property
    def extra_state_attributes(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return {}

        return {
            "end": next_event["end_iso"],
            "subject": next_event["subject"],
        }


class RoomNextStartsInSensor(BaseRoomSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(
            coordinator,
            entry,
            "next_meeting_starts_in",
            "Next Meeting Starts In",
        )
        self._attr_icon = "mdi:timer-outline"

    @property
    def native_value(self):
        _, next_event, _ = self._get_live_events()

        return _seconds_until(next_event, self.coordinator.tz)

    @property
    def extra_state_attributes(self):
        _, next_event, _ = self._get_live_events()

        if not next_event:
            return {}

        return {
            "minutes_until_start": _minutes_until(next_event, self.coordinator.tz),
            "subject": next_event["subject"],
            "start": next_event["start_iso"],
            "start_time": next_event["start_time"],
        }