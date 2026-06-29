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
    CONF_ROOMS,
    CONF_LOOKAHEAD_DAYS,
    CONF_MAX_EVENTS,
    CONF_TIMEZONE,
)

_LOGGER = logging.getLogger(__name__)

class GraphRoomCalendarCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.tenant_id = entry.data[CONF_TENANT_ID]
        self.client_id = entry.data[CONF_CLIENT_ID]
        self.client_secret = entry.data[CONF_CLIENT_SECRET]
        self.rooms = entry.data[CONF_ROOMS]
        self.lookahead_days = entry.data[CONF_LOOKAHEAD_DAYS]
        self.max_events = entry.data[CONF_MAX_EVENTS]
        self.tz_name = entry.data[CONF_TIMEZONE]
        self.tz = ZoneInfo(self.tz_name)
        self._token: str | None = None
        self._token_expires: datetime | None = None

        update_interval = timedelta(seconds=entry.data.get("update_interval", 60))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_get_token(self) -> str:
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
                raise UpdateFailed(f"Token request failed: {resp.status} {data}")

        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._token_expires = now + timedelta(seconds=max(60, expires_in - 120))
        return self._token

    def _parse_graph_datetime(self, value: str) -> datetime:
        # Graph often returns naive local DateTime when Prefer: outlook.timezone is used.
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tz)
        return dt.astimezone(self.tz)

    async def _async_update_data(self):
        token = await self._async_get_token()
        now = datetime.now(self.tz)
        end = now + timedelta(days=self.lookahead_days)

        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": f'outlook.timezone="{self.tz_name}"',
        }
        params = {
            "startDateTime": now.isoformat(),
            "endDateTime": end.isoformat(),
            "$select": "subject,start,end,location,organizer,isCancelled,showAs,bodyPreview",
            "$orderby": "start/dateTime",
            "$top": "50",
        }

        per_room = {}
        all_events = []

        for room in self.rooms:
            room_events = []
            encoded_room = quote(room, safe="")
            url = f"https://graph.microsoft.com/v1.0/users/{encoded_room}/calendar/calendarView"

            while url:
                async with self.session.get(url, headers=headers, params=params if "?" not in url else None) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status >= 400:
                        raise UpdateFailed(f"Graph request failed for {room}: {resp.status} {data}")

                for ev in data.get("value", []):
                    if ev.get("isCancelled"):
                        continue

                    start = self._parse_graph_datetime(ev["start"]["dateTime"])
                    finish = self._parse_graph_datetime(ev["end"]["dateTime"])
                    subject = unescape(ev.get("subject") or "Reserved")
                    location = ev.get("location", {}).get("displayName")

                    item = {
                        "room": room,
                        "subject": subject,
                        "start": start,
                        "end": finish,
                        "start_iso": start.isoformat(),
                        "end_iso": finish.isoformat(),
                        "start_time": start.strftime("%H:%M"),
                        "end_time": finish.strftime("%H:%M"),
                        "date": start.strftime("%Y-%m-%d"),
                        "location": location,
                        "show_as": ev.get("showAs"),
                        "occupied": start <= now <= finish,
                    }
                    room_events.append(item)
                    all_events.append(item)

                url = data.get("@odata.nextLink")
                params = None

            room_events.sort(key=lambda e: e["start"])
            future_events = [e for e in room_events if e["end"] > now]
            per_room[room] = {
                "events": future_events[: self.max_events],
                "next": future_events[0] if future_events else None,
                "occupied": any(e["occupied"] for e in future_events),
            }

        all_events.sort(key=lambda e: e["start"])
        future_all = [e for e in all_events if e["end"] > now]

        # Make datetime objects JSON/attribute friendly.
        def clean(e):
            if not e:
                return None
            return {k: v for k, v in e.items() if k not in ("start", "end")}

        return {
            "rooms": {
                room: {
                    "events": [clean(e) for e in data["events"]],
                    "next": clean(data["next"]),
                    "occupied": data["occupied"],
                }
                for room, data in per_room.items()
            },
            "all_next": clean(future_all[0]) if future_all else None,
            "all_events": [clean(e) for e in future_all[: self.max_events]],
            "last_update": now.isoformat(),
        }
