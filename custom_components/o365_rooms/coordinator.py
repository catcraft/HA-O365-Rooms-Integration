from __future__ import annotations

import logging
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import quote
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_TENANT_ID,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ROOM,
    CONF_ROOMS,
    CONF_LOOKAHEAD_DAYS,
    CONF_PAST_DAYS,
    CONF_MAX_EVENTS,
    CONF_TIMEZONE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PAST_DAYS,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class GraphRoomCalendarCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        self.session = async_get_clientsession(hass)

        self.tenant_id = entry.data[CONF_TENANT_ID]
        self.client_id = entry.data[CONF_CLIENT_ID]
        self.client_secret = entry.data[CONF_CLIENT_SECRET]

        # New config uses one room mailbox.
        # Legacy fallback supports old entries with "rooms".
        self.room = self._get_room_from_entry(entry)

        self.lookahead_days = entry.data[CONF_LOOKAHEAD_DAYS]
        self.past_days = entry.data.get(CONF_PAST_DAYS, DEFAULT_PAST_DAYS)
        self.max_events = entry.data[CONF_MAX_EVENTS]

        self.tz_name = entry.data[CONF_TIMEZONE]
        self.tz = ZoneInfo(self.tz_name)

        self._token = None
        self._token_expires = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.room}",
            update_interval=timedelta(
                seconds=entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ),
        )

    def _get_room_from_entry(self, entry) -> str:
        if CONF_ROOM in entry.data:
            return entry.data[CONF_ROOM]

        # Legacy fallback for old multi-room config.
        rooms = entry.data.get(CONF_ROOMS, [])
        if isinstance(rooms, list) and rooms:
            return rooms[0]

        raise UpdateFailed("No room mailbox configured")

    async def _async_get_token(self):
        now = datetime.now(self.tz)

        if self._token and self._token_expires and now < self._token_expires:
            return self._token

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        async with self.session.post(url, data=payload) as resp:
            data = await resp.json(content_type=None)

            if resp.status >= 400:
                raise UpdateFailed(f"Token failed: {resp.status} {data}")

        self._token = data["access_token"]

        expires_in = int(data.get("expires_in", 3600))
        self._token_expires = now + timedelta(seconds=max(expires_in - 60, 60))

        return self._token

    def _parse_dt(self, value: str) -> datetime:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tz)

        return dt.astimezone(self.tz)

    def _format_event(self, ev: dict, now: datetime) -> dict:
        start = self._parse_dt(ev["start"]["dateTime"])
        end = self._parse_dt(ev["end"]["dateTime"])

        return {
            "room": self.room,
            "subject": unescape(ev.get("subject") or "Reserved"),
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "date": start.date().isoformat(),
            "start_time": start.strftime("%H:%M"),
            "end_time": end.strftime("%H:%M"),
            "occupied": start <= now < end,
        }

    async def _fetch_calendar_view(
        self,
        token: str,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> list[dict]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": f'outlook.timezone="{self.tz_name}"',
        }

        params = {
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$select": "subject,start,end,isCancelled",
            "$orderby": "start/dateTime asc",
        }

        url = f"https://graph.microsoft.com/v1.0/users/{quote(self.room)}/calendar/calendarView"

        events = []
        first_request = True

        while url:
            async with self.session.get(
                url,
                headers=headers,
                params=params if first_request else None,
            ) as resp:
                data = await resp.json(content_type=None)

                if resp.status >= 400:
                    raise UpdateFailed(f"{self.room} failed: {data}")

            first_request = False

            for ev in data.get("value", []):
                if ev.get("isCancelled"):
                    continue

                events.append(self._format_event(ev, now))

            url = data.get("@odata.nextLink")

        events.sort(key=lambda item: item["start_iso"])
        return events

    async def _async_update_data(self):
        token = await self._async_get_token()
        now = datetime.now(self.tz)

        past_start = now - timedelta(days=self.past_days)
        future_end = now + timedelta(days=self.lookahead_days)

        past_events = await self._fetch_calendar_view(
            token=token,
            start=past_start,
            end=now,
            now=now,
        )

        future_events = await self._fetch_calendar_view(
            token=token,
            start=now,
            end=future_end,
            now=now,
        )

        # filter future
        future_events = [
            event for event in future_events
            if event["end_iso"] > now.isoformat()
        ]

        current_event = None
        future_upcoming = []
        past_ended = []

        for event in future_events:
            if event["occupied"]:
                current_event = event
            else:
                future_upcoming.append(event)

        for event in past_events:
            if event["end_iso"] <= now.isoformat():
                past_ended.append(event)

        future_upcoming.sort(key=lambda e: e["start_iso"])
        past_ended.sort(key=lambda e: e["end_iso"])

        next_event = future_upcoming[0] if future_upcoming else None
        last_event = past_ended[-1] if past_ended else None

        return {
            "room": self.room,
            "current": current_event,
            "next": next_event,
            "last": last_event,
            "occupied": current_event is not None,
            "last_update": now.isoformat(),
        }