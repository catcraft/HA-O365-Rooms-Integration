from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_TENANT_ID,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ROOM,
    CONF_LOOKAHEAD_DAYS,
    CONF_PAST_DAYS,
    CONF_MAX_EVENTS,
    CONF_UPDATE_INTERVAL,
    CONF_TIMEZONE,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_PAST_DAYS,
    DEFAULT_MAX_EVENTS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TIMEZONE,
)


class O365RoomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            room = user_input[CONF_ROOM].strip().lower()

            if not room:
                errors[CONF_ROOM] = "room_required"
            else:
                data = dict(user_input)
                data[CONF_ROOM] = room

                await self.async_set_unique_id(
                    f"{data[CONF_CLIENT_ID]}_{room}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, room),
                    data=data,
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="O365 Room Calendar"): str,
                vol.Required(CONF_TENANT_ID): str,
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_ROOM, default="room@domain.com"): str,
                vol.Optional(CONF_TIMEZONE, default=DEFAULT_TIMEZONE): str,
                vol.Optional(CONF_LOOKAHEAD_DAYS, default=DEFAULT_LOOKAHEAD_DAYS): int,
                vol.Optional(CONF_PAST_DAYS, default=DEFAULT_PAST_DAYS): int,
                vol.Optional(CONF_MAX_EVENTS, default=DEFAULT_MAX_EVENTS): int,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )