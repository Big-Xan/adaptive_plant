"""Constants for the Adaptive Plant integration."""

DOMAIN = "adaptive_plant"

PLATFORMS = ["sensor", "button", "number", "select", "text"]

# ── Config entry data keys (set at setup, not user-editable after) ─────────────
CONF_PLANT_NAME = "plant_name"
CONF_EARLY_WATERING_THRESHOLD = "early_watering_threshold"
CONF_HEALTH_PROMPT_INTERVAL = "health_prompt_interval_days"
CONF_ENABLE_FERTILIZATION = "enable_fertilization"
CONF_ENABLE_NOTES = "enable_notes"
CONF_ENABLE_IMAGE = "enable_image"
CONF_IMAGE_PATH = "image_path"
CONF_MOISTURE_SENSOR = "moisture_sensor"
CONF_DRY_THRESHOLD = "dry_threshold"
CONF_WET_THRESHOLD = "wet_threshold"

# ── Config entry options keys (mutable at runtime) ─────────────────────────────
OPT_WATERING_INTERVAL = "watering_interval_days"
OPT_FERTILIZATION_INTERVAL = "fertilization_interval_days"

# ── State keys (stored in config entry options) ────────────────────────────────
STATE_LAST_WATERED = "last_watered"
STATE_NEXT_WATERING = "next_watering"
STATE_EARLY_WATERING_COUNT = "early_watering_count"
STATE_HEALTH = "health"
STATE_HEALTH_LAST_UPDATED = "health_last_updated"
STATE_LAST_FERTILIZED = "last_fertilized"
STATE_NEXT_FERTILIZED = "next_fertilized"
STATE_NOTES = "notes"

# ── Health select options ──────────────────────────────────────────────────────
HEALTH_OPTIONS = ["Excellent", "Good", "Poor", "Sick"]
DEFAULT_HEALTH = "Good"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_WATERING_INTERVAL = 7
DEFAULT_EARLY_WATERING_THRESHOLD = 3
DEFAULT_HEALTH_PROMPT_INTERVAL = 14
DEFAULT_FERTILIZATION_INTERVAL = 30

# ── Misc ──────────────────────────────────────────────────────────────────────
NOTIFICATION_ID_PREFIX = "adaptive_plant_health_"
CONF_AREA = "area"
CONF_INITIAL_LAST_WATERED = "initial_last_watered"
CONF_INITIAL_NEXT_WATERING = "initial_next_watering"
CONF_INITIAL_LAST_FERTILIZED = "initial_last_fertilized"
CONF_INITIAL_NEXT_FERTILIZED = "initial_next_fertilized"
CONF_SNOOZE_THRESHOLD = "snooze_threshold"
STATE_SNOOZE_COUNT = "snooze_count"
STATE_SNOOZED_THIS_PERIOD = "snoozed_this_period"
DEFAULT_SNOOZE_THRESHOLD = 3