# O365 Rooms Calendar

Home Assistant custom integration for HACS that reads Microsoft 365 room mailbox calendars through Microsoft Graph and creates sensors for the next meetings.

## Features

- UI setup via Home Assistant config flow
- Multiple room mailboxes
- One sensor per room
- One combined next-meeting sensor
- Uses Microsoft Graph application permissions
- Returns useful attributes for dashboards: start, end, occupied, next event and event list

## Required Microsoft Graph permission

Your Azure App Registration needs:

- `Calendars.Read` as **Application** permission
- Admin consent granted

## HACS repository structure

```text
custom_components/o365_rooms/__init__.py
custom_components/o365_rooms/config_flow.py
custom_components/o365_rooms/const.py
custom_components/o365_rooms/coordinator.py
custom_components/o365_rooms/manifest.json
custom_components/o365_rooms/sensor.py
custom_components/o365_rooms/translations/en.json
brand/icon.png
hacs.json
README.md
```

## Installation via HACS custom repository

Add via Custom Repository

## Created entities

Example entities:

- `sensor.all_rooms_next_meeting`

The exact entity IDs can be changed in Home Assistant.

## Sensor attributes

Each room sensor includes attributes like:

- `occupied`
- `start`
- `end`
- `start_time`
- `end_time`
- `next`
- `events`

## Notes

- This integration uses cloud polling against Microsoft Graph.
- The default timezone is `Europe/Zurich`.
- The default lookahead range is 7 days.
- The default update interval is 60 seconds.