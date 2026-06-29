DOMAIN = "o365_rooms"

CONF_TENANT_ID = "tenant_id"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

# New clean config: one integration instance = one mailbox
CONF_ROOM = "room"

# Legacy fallback, so old entries do not instantly explode
CONF_ROOMS = "rooms"

CONF_LOOKAHEAD_DAYS = "lookahead_days"
CONF_PAST_DAYS = "past_days"
CONF_MAX_EVENTS = "max_events"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TIMEZONE = "timezone"

DEFAULT_LOOKAHEAD_DAYS = 7
DEFAULT_PAST_DAYS = 30
DEFAULT_MAX_EVENTS = 5
DEFAULT_UPDATE_INTERVAL = 7200
DEFAULT_TIMEZONE = "Europe/Zurich"