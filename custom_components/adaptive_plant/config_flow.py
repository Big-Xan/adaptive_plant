"""Config flow for the Adaptive Plant integration."""
from __future__ import annotations

from datetime import date, timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AREA,
    CONF_DRY_THRESHOLD,
    CONF_EARLY_WATERING_THRESHOLD,
    CONF_ENABLE_FERTILIZATION,
    CONF_ENABLE_IMAGE,
    CONF_ENABLE_LATIN_NAME,
    CONF_ENABLE_NOTES,
    CONF_ENABLE_REPOTTING,
    CONF_FERTILIZATION_ENABLED,
    CONF_HEALTH_PROMPT_INTERVAL,
    CONF_IMAGE_PATH,
    CONF_INITIAL_LAST_FERTILIZED,
    CONF_INITIAL_LAST_WATERED,
    CONF_LABEL,
    CONF_LATIN_NAME,
    CONF_MOISTURE_SENSOR,
    CONF_NOTES_ENABLED,
    CONF_PLANT_NAME,
    CONF_REPOTTING_ENABLED,
    CONF_RESOLVED_LAST_REPOTTED,
    CONF_SNOOZE_THRESHOLD,
    CONF_WET_THRESHOLD,
    DEFAULT_EARLY_WATERING_THRESHOLD,
    DEFAULT_FERTILIZATION_INTERVAL,
    DEFAULT_HEALTH_PROMPT_INTERVAL,
    DEFAULT_SNOOZE_THRESHOLD,
    DEFAULT_WATERING_INTERVAL,
    DOMAIN,
    OPT_FERTILIZATION_INTERVAL,
    OPT_WATERING_INTERVAL,
    STATE_LAST_FERTILIZED,
    STATE_LAST_REPOTTED,
    STATE_NEXT_FERTILIZED,
)

WATERING_DATE_TODAY = "today"
WATERING_DATE_YESTERDAY = "yesterday"
WATERING_DATE_CUSTOM = "custom"
WATERING_DATE_NEVER = "never"

CONF_INITIAL_LAST_REPOTTED = "initial_last_repotted"


def _basic_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_PLANT_NAME, default=defaults.get(CONF_PLANT_NAME, "")): selector.selector({"text": {}}),
        vol.Optional(CONF_AREA): selector.selector({"area": {}}),
        vol.Optional(CONF_LABEL, default=defaults.get(CONF_LABEL, "")): selector.selector({"text": {}}),
        vol.Required(OPT_WATERING_INTERVAL, default=defaults.get(OPT_WATERING_INTERVAL, DEFAULT_WATERING_INTERVAL)): selector.selector(
            {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
        ),
        vol.Required(CONF_EARLY_WATERING_THRESHOLD, default=defaults.get(CONF_EARLY_WATERING_THRESHOLD, DEFAULT_EARLY_WATERING_THRESHOLD)): selector.selector(
            {"number": {"min": 1, "max": 30, "mode": "box", "unit_of_measurement": "times"}}
        ),
        vol.Required(CONF_SNOOZE_THRESHOLD, default=defaults.get(CONF_SNOOZE_THRESHOLD, DEFAULT_SNOOZE_THRESHOLD)): selector.selector(
            {"number": {"min": 1, "max": 30, "mode": "box", "unit_of_measurement": "times"}}
        ),
        vol.Required(CONF_HEALTH_PROMPT_INTERVAL, default=defaults.get(CONF_HEALTH_PROMPT_INTERVAL, DEFAULT_HEALTH_PROMPT_INTERVAL)): selector.selector(
            {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
        ),
    })


def _features_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ENABLE_FERTILIZATION, default=defaults.get(CONF_ENABLE_FERTILIZATION, False)): selector.selector({"boolean": {}}),
        vol.Required(CONF_ENABLE_NOTES, default=defaults.get(CONF_ENABLE_NOTES, False)): selector.selector({"boolean": {}}),
        vol.Required(CONF_ENABLE_LATIN_NAME, default=defaults.get(CONF_ENABLE_LATIN_NAME, False)): selector.selector({"boolean": {}}),
        vol.Required(CONF_ENABLE_IMAGE, default=defaults.get(CONF_ENABLE_IMAGE, False)): selector.selector({"boolean": {}}),
        vol.Required(CONF_ENABLE_REPOTTING, default=defaults.get(CONF_ENABLE_REPOTTING, False)): selector.selector({"boolean": {}}),
        vol.Optional(CONF_MOISTURE_SENSOR): selector.selector(
            {"entity": {"domain": "sensor", "multiple": False}}
        ),
    })


def _last_watered_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_INITIAL_LAST_WATERED, default=WATERING_DATE_TODAY): selector.selector({
            "select": {
                "options": [
                    {"value": WATERING_DATE_TODAY, "label": "Today"},
                    {"value": WATERING_DATE_YESTERDAY, "label": "Yesterday"},
                    {"value": WATERING_DATE_CUSTOM, "label": "Enter a custom date"},
                    {"value": WATERING_DATE_NEVER, "label": "Haven't watered yet"},
                ],
                "mode": "list",
            }
        }),
    })


def _last_watered_custom_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required("custom_watered_date"): selector.selector({"date": {}}),
    })


def _last_fertilized_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_INITIAL_LAST_FERTILIZED, default=WATERING_DATE_TODAY): selector.selector({
            "select": {
                "options": [
                    {"value": WATERING_DATE_TODAY, "label": "Today"},
                    {"value": WATERING_DATE_YESTERDAY, "label": "Yesterday"},
                    {"value": WATERING_DATE_CUSTOM, "label": "Enter a custom date"},
                    {"value": WATERING_DATE_NEVER, "label": "Haven't fertilized yet"},
                ],
                "mode": "list",
            }
        }),
    })


def _last_fertilized_custom_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required("custom_fertilized_date"): selector.selector({"date": {}}),
    })


def _last_repotted_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_INITIAL_LAST_REPOTTED, default=WATERING_DATE_TODAY): selector.selector({
            "select": {
                "options": [
                    {"value": WATERING_DATE_TODAY, "label": "Today"},
                    {"value": WATERING_DATE_YESTERDAY, "label": "Yesterday"},
                    {"value": WATERING_DATE_CUSTOM, "label": "Enter a custom date"},
                    {"value": WATERING_DATE_NEVER, "label": "Haven't repotted yet"},
                ],
                "mode": "list",
            }
        }),
    })


def _last_repotted_custom_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required("custom_repotted_date"): selector.selector({"date": {}}),
    })


def _fertilize_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(OPT_FERTILIZATION_INTERVAL, default=defaults.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL)): selector.selector(
            {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
        ),
    })


def _latin_name_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_LATIN_NAME, default=defaults.get(CONF_LATIN_NAME, "")): selector.selector(
            {"text": {}}
        ),
    })


def _image_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_IMAGE_PATH, default=defaults.get(CONF_IMAGE_PATH, "")): selector.selector(
            {"text": {}}
        ),
    })


def _moisture_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_DRY_THRESHOLD, default=defaults.get(CONF_DRY_THRESHOLD, 30.0)): selector.selector(
            {"number": {"min": 0, "max": 100, "step": 0.1, "mode": "box"}}
        ),
        vol.Required(CONF_WET_THRESHOLD, default=defaults.get(CONF_WET_THRESHOLD, 70.0)): selector.selector(
            {"number": {"min": 0, "max": 100, "step": 0.1, "mode": "box"}}
        ),
    })


def _resolve_date(selection: str, custom_date: str | None, interval: int) -> tuple[str | None, str]:
    today = date.today()
    if selection == WATERING_DATE_TODAY:
        last = today
    elif selection == WATERING_DATE_YESTERDAY:
        last = today - timedelta(days=1)
    elif selection == WATERING_DATE_CUSTOM and custom_date:
        try:
            last = date.fromisoformat(custom_date)
        except ValueError:
            last = today
    else:
        return None, today.isoformat()
    next_date = last + timedelta(days=interval)
    return last.isoformat(), next_date.isoformat()


class AdaptivePlantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of an Adaptive Plant config entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            plant_name = user_input.get(CONF_PLANT_NAME, "").strip()
            if not plant_name:
                errors[CONF_PLANT_NAME] = "name_required"
            else:
                self._data.update({k: v for k, v in user_input.items() if v not in (None, "")})
                self._data[CONF_PLANT_NAME] = plant_name
                return await self.async_step_features()
        return self.async_show_form(step_id="user", data_schema=_basic_schema(self._data), errors=errors)

    async def async_step_features(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            for k, v in user_input.items():
                if v not in (None, ""):
                    self._data[k] = v
            return await self.async_step_last_watered()
        return self.async_show_form(step_id="features", data_schema=_features_schema(self._data))

    async def async_step_last_watered(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            selection = user_input[CONF_INITIAL_LAST_WATERED]
            self._data[CONF_INITIAL_LAST_WATERED] = selection
            if selection == WATERING_DATE_CUSTOM:
                return await self.async_step_last_watered_custom()
            last, nxt = _resolve_date(selection, None, self._data.get(OPT_WATERING_INTERVAL, DEFAULT_WATERING_INTERVAL))
            self._data["_resolved_last_watered"] = last
            self._data["_resolved_next_watering"] = nxt
            return await self._after_watering()
        return self.async_show_form(step_id="last_watered", data_schema=_last_watered_schema())

    async def async_step_last_watered_custom(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            custom_date = user_input.get("custom_watered_date", "")
            try:
                date.fromisoformat(custom_date)
            except ValueError:
                errors["custom_watered_date"] = "invalid_date"
            else:
                last, nxt = _resolve_date(WATERING_DATE_CUSTOM, custom_date, self._data.get(OPT_WATERING_INTERVAL, DEFAULT_WATERING_INTERVAL))
                self._data["_resolved_last_watered"] = last
                self._data["_resolved_next_watering"] = nxt
                return await self._after_watering()
        return self.async_show_form(step_id="last_watered_custom", data_schema=_last_watered_custom_schema(), errors=errors)

    async def _after_watering(self) -> FlowResult:
        if self._data.get(CONF_ENABLE_FERTILIZATION):
            return await self.async_step_fertilize()
        if self._data.get(CONF_ENABLE_REPOTTING):
            return await self.async_step_last_repotted()
        if self._data.get(CONF_ENABLE_LATIN_NAME):
            return await self.async_step_latin_name()
        if self._data.get(CONF_ENABLE_IMAGE):
            return await self.async_step_image()
        if self._data.get(CONF_MOISTURE_SENSOR):
            return await self.async_step_moisture()
        return self._create_entry()

    async def async_step_fertilize(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_last_fertilized()
        return self.async_show_form(step_id="fertilize", data_schema=_fertilize_schema(self._data))

    async def async_step_last_fertilized(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            selection = user_input[CONF_INITIAL_LAST_FERTILIZED]
            self._data[CONF_INITIAL_LAST_FERTILIZED] = selection
            if selection == WATERING_DATE_CUSTOM:
                return await self.async_step_last_fertilized_custom()
            last, nxt = _resolve_date(selection, None, self._data.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL))
            self._data["_resolved_last_fertilized"] = last
            self._data["_resolved_next_fertilized"] = nxt
            return await self._after_fertilizing()
        return self.async_show_form(step_id="last_fertilized", data_schema=_last_fertilized_schema())

    async def async_step_last_fertilized_custom(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            custom_date = user_input.get("custom_fertilized_date", "")
            try:
                date.fromisoformat(custom_date)
            except ValueError:
                errors["custom_fertilized_date"] = "invalid_date"
            else:
                last, nxt = _resolve_date(WATERING_DATE_CUSTOM, custom_date, self._data.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL))
                self._data["_resolved_last_fertilized"] = last
                self._data["_resolved_next_fertilized"] = nxt
                return await self._after_fertilizing()
        return self.async_show_form(step_id="last_fertilized_custom", data_schema=_last_fertilized_custom_schema(), errors=errors)

    async def _after_fertilizing(self) -> FlowResult:
        if self._data.get(CONF_ENABLE_REPOTTING):
            return await self.async_step_last_repotted()
        if self._data.get(CONF_ENABLE_LATIN_NAME):
            return await self.async_step_latin_name()
        if self._data.get(CONF_ENABLE_IMAGE):
            return await self.async_step_image()
        if self._data.get(CONF_MOISTURE_SENSOR):
            return await self.async_step_moisture()
        return self._create_entry()

    async def async_step_last_repotted(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            selection = user_input[CONF_INITIAL_LAST_REPOTTED]
            self._data[CONF_INITIAL_LAST_REPOTTED] = selection
            if selection == WATERING_DATE_CUSTOM:
                return await self.async_step_last_repotted_custom()
            if selection != WATERING_DATE_NEVER:
                today = date.today()
                if selection == WATERING_DATE_TODAY:
                    last = today
                else:  # yesterday
                    last = today - timedelta(days=1)
                self._data[CONF_RESOLVED_LAST_REPOTTED] = last.isoformat()
            # "never" → leave CONF_RESOLVED_LAST_REPOTTED absent
            return await self._after_repotting()
        return self.async_show_form(step_id="last_repotted", data_schema=_last_repotted_schema())

    async def async_step_last_repotted_custom(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            custom_date = user_input.get("custom_repotted_date", "")
            try:
                date.fromisoformat(custom_date)
            except ValueError:
                errors["custom_repotted_date"] = "invalid_date"
            else:
                self._data[CONF_RESOLVED_LAST_REPOTTED] = custom_date
                return await self._after_repotting()
        return self.async_show_form(
            step_id="last_repotted_custom",
            data_schema=_last_repotted_custom_schema(),
            errors=errors,
        )

    async def _after_repotting(self) -> FlowResult:
        if self._data.get(CONF_ENABLE_LATIN_NAME):
            return await self.async_step_latin_name()
        if self._data.get(CONF_ENABLE_IMAGE):
            return await self.async_step_image()
        if self._data.get(CONF_MOISTURE_SENSOR):
            return await self.async_step_moisture()
        return self._create_entry()

    async def async_step_latin_name(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            name = user_input.get(CONF_LATIN_NAME, "").strip()
            if name:
                self._data[CONF_LATIN_NAME] = name
            if self._data.get(CONF_ENABLE_IMAGE):
                return await self.async_step_image()
            if self._data.get(CONF_MOISTURE_SENSOR):
                return await self.async_step_moisture()
            return self._create_entry()
        return self.async_show_form(
            step_id="latin_name",
            data_schema=_latin_name_schema(self._data),
        )

    async def async_step_image(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            path = user_input.get(CONF_IMAGE_PATH, "").strip()
            if path and not path.startswith("/local/"):
                errors[CONF_IMAGE_PATH] = "invalid_image_path"
            else:
                self._data[CONF_IMAGE_PATH] = path or None
                if self._data.get(CONF_MOISTURE_SENSOR):
                    return await self.async_step_moisture()
                return self._create_entry()
        return self.async_show_form(
            step_id="image",
            data_schema=_image_schema(self._data),
            errors=errors,
        )

    async def async_step_moisture(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            dry = user_input.get(CONF_DRY_THRESHOLD)
            wet = user_input.get(CONF_WET_THRESHOLD)
            if dry is not None and wet is not None and dry >= wet:
                errors["base"] = "dry_above_wet"
            else:
                self._data.update(user_input)
                return self._create_entry()
        return self.async_show_form(step_id="moisture", data_schema=_moisture_schema(self._data), errors=errors)

    def _create_entry(self) -> FlowResult:
        return self.async_create_entry(title=self._data[CONF_PLANT_NAME], data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AdaptivePlantOptionsFlow(config_entry)


class AdaptivePlantOptionsFlow(OptionsFlow):
    """Allow editing mutable settings after the entry is created."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        # Stash the moisture sensor choice from step 1 so step 2 knows what was picked
        self._pending_moisture_sensor: str | None = None
        # Stash cleaned options while we run a sub-flow (fertilize/repot init)
        self._pending_opts: dict = {}
        # Flags set when a first-enable sub-flow is in progress
        self._pending_fert_first: bool = False
        self._pending_repot_first: bool = False
        # True when the user submitted a blank or "null" label in step 1 —
        # carried so the moisture-options step can remove the stored label.
        self._pending_clear_label: bool = False

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self._config_entry
        current_opts = entry.options

        if user_input is not None:
            # Detect label-clear intent up front (blank, whitespace-only, or
            # the literal word "null"). The cleanup loop further down only
            # catches blanks AND only runs on the no-moisture branch, so we
            # need to capture intent here and apply it explicitly to `merged`
            # in both branches.
            raw_label = user_input.get(CONF_LABEL, "")
            label_stripped = raw_label.strip() if isinstance(raw_label, str) else ""
            clear_label = (not label_stripped) or label_stripped.lower() == "null"

            cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}

            # Normalise label: drop from `cleaned` unconditionally, then re-add
            # the stripped value only if the user didn't intend to clear it.
            # `merged` cleanup below handles removing any existing stored value.
            cleaned.pop(CONF_LABEL, None)
            if not clear_label:
                cleaned[CONF_LABEL] = label_stripped

            # Notes enabled toggle — always write explicitly so falsy value persists
            cleaned[CONF_NOTES_ENABLED] = bool(user_input.get(CONF_NOTES_ENABLED, False))

            # Fertilization enabled toggle — always write explicitly.
            cleaned[CONF_FERTILIZATION_ENABLED] = bool(user_input.get(CONF_FERTILIZATION_ENABLED, False))

            # Repotting enabled toggle — always write explicitly.
            cleaned[CONF_REPOTTING_ENABLED] = bool(user_input.get(CONF_REPOTTING_ENABLED, False))

            # Latin name toggle — write explicitly, and handle the text field.
            latin_enabled = bool(user_input.get(CONF_ENABLE_LATIN_NAME, False))
            cleaned[CONF_ENABLE_LATIN_NAME] = latin_enabled
            if latin_enabled:
                # Use key-presence check so empty string is treated as intentional clear
                raw_latin = user_input.get(CONF_LATIN_NAME, "")
                cleaned[CONF_LATIN_NAME] = raw_latin.strip() if raw_latin else ""
            else:
                # Toggle off — remove stored latin name
                cleaned.pop(CONF_LATIN_NAME, None)

            # Image toggle — write explicitly, and handle the text field.
            # Empty string is written as a tombstone (mirroring CONF_LABEL and
            # CONF_LATIN_NAME) so the PlantData.image_path property's fallback
            # to entry.data doesn't resurface a stale value set during the
            # original setup wizard.
            image_enabled = bool(user_input.get(CONF_ENABLE_IMAGE, False))
            cleaned[CONF_ENABLE_IMAGE] = image_enabled
            if image_enabled:
                raw_image = user_input.get(CONF_IMAGE_PATH, "")
                cleaned[CONF_IMAGE_PATH] = raw_image.strip() if raw_image else ""
            else:
                cleaned.pop(CONF_IMAGE_PATH, None)

            # Handle moisture sensor selection.
            # The toggle is the authoritative clear mechanism — if it's off we
            # strip the sensor and thresholds regardless of the picker value,
            # since the HA entity selector can't be truly blanked in the UI.
            moisture_enabled = user_input.get("moisture_sensor_enabled", False)
            moisture_raw = user_input.get(CONF_MOISTURE_SENSOR) if moisture_enabled else None
            # Remove the toggle key — it's UI-only, not stored in options
            cleaned.pop("moisture_sensor_enabled", None)

            if moisture_raw:
                self._pending_moisture_sensor = moisture_raw
                # Carry non-moisture fields forward so they're saved after thresholds
                self._pending_opts = cleaned
                # Carry the clear-label intent forward — step 2's merge would
                # otherwise pull the stale value back in from current_opts.
                self._pending_clear_label = clear_label
                return await self.async_step_moisture_options()
            else:
                # Sensor cleared — tombstone the sensor and strip thresholds.
                # The sensor key gets an empty-string tombstone (not a pop)
                # because PlantData.moisture_sensor falls back to entry.data
                # when the key is missing — popping would resurrect a sensor
                # chosen during the original setup wizard. The thresholds are
                # popped: every moisture code path gates on moisture_sensor
                # first, so their entry.data fallback is inert.
                merged = {**current_opts, **cleaned}
                for key in (CONF_DRY_THRESHOLD, CONF_WET_THRESHOLD):
                    merged.pop(key, None)
                merged[CONF_MOISTURE_SENSOR] = ""
                # Explicit label clear — write an empty-string tombstone rather
                # than popping the key. The PlantData.label property falls
                # back to entry.data when CONF_LABEL is missing from options,
                # so a pop leaves a stale value from setup visible. An empty
                # string in options is treated as "cleared" by the property
                # and shadows the entry.data fallback.
                if clear_label:
                    merged[CONF_LABEL] = ""
                # Also clear blanked fields — but skip keys we've already
                # handled explicitly above. Tombstone keys (CONF_LABEL,
                # CONF_LATIN_NAME, CONF_IMAGE_PATH, CONF_MOISTURE_SENSOR) are
                # included because their empty-string tombstones written
                # earlier are intentional — the loop would otherwise treat
                # "" as a blank and delete them, falling back to stale
                # entry.data values from the original setup wizard.
                _skip_clear = {
                    CONF_LABEL,
                    CONF_LATIN_NAME,
                    CONF_IMAGE_PATH,
                    CONF_MOISTURE_SENSOR,
                    CONF_NOTES_ENABLED,
                    CONF_ENABLE_LATIN_NAME,
                    CONF_FERTILIZATION_ENABLED,
                    CONF_REPOTTING_ENABLED,
                    CONF_ENABLE_IMAGE,
                }
                for k, v in user_input.items():
                    if k not in _skip_clear and v in (None, "") and k in merged:
                        del merged[k]

                # ── First-enable detection ────────────────────────────────────
                # Fertilization: toggle just turned on AND no last_fertilized yet
                fert_first_enable = (
                    cleaned.get(CONF_FERTILIZATION_ENABLED) is True
                    and STATE_LAST_FERTILIZED not in current_opts
                )
                # Repotting: toggle just turned on AND no last_repotted yet
                repot_first_enable = (
                    cleaned.get(CONF_REPOTTING_ENABLED) is True
                    and STATE_LAST_REPOTTED not in current_opts
                )

                if fert_first_enable or repot_first_enable:
                    # Stash the fully-merged options so the sub-flow can write
                    # them once it has collected the missing dates.
                    self._pending_opts = merged
                    self._pending_fert_first = fert_first_enable
                    self._pending_repot_first = repot_first_enable
                    if fert_first_enable:
                        return await self.async_step_fertilized_init()
                    return await self.async_step_repotted_init()

                return self.async_create_entry(title="", data=merged)

        defaults = {**entry.data, **current_opts}

        # Resolve the currently active moisture sensor. Key-presence check
        # (mirroring PlantData.moisture_sensor) so the empty-string tombstone
        # written on disable shadows entry.data — an `or` chain here would
        # fall through the tombstone and re-show the stale setup-wizard
        # sensor with the toggle defaulted back on.
        if CONF_MOISTURE_SENSOR in current_opts:
            current_moisture = current_opts[CONF_MOISTURE_SENSOR] or None
        else:
            current_moisture = entry.data.get(CONF_MOISTURE_SENSOR)

        schema_fields: dict = {
            vol.Optional(
                CONF_LABEL,
                description={"suggested_value": defaults.get(CONF_LABEL, "")},
            ): selector.selector({"text": {}}),
            vol.Required(OPT_WATERING_INTERVAL, default=defaults.get(OPT_WATERING_INTERVAL, DEFAULT_WATERING_INTERVAL)): selector.selector(
                {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
            ),
            vol.Required(CONF_EARLY_WATERING_THRESHOLD, default=defaults.get(CONF_EARLY_WATERING_THRESHOLD, DEFAULT_EARLY_WATERING_THRESHOLD)): selector.selector(
                {"number": {"min": 1, "max": 30, "mode": "box", "unit_of_measurement": "times"}}
            ),
            vol.Required(CONF_SNOOZE_THRESHOLD, default=defaults.get(CONF_SNOOZE_THRESHOLD, DEFAULT_SNOOZE_THRESHOLD)): selector.selector(
                {"number": {"min": 1, "max": 30, "mode": "box", "unit_of_measurement": "times"}}
            ),
            vol.Required(CONF_HEALTH_PROMPT_INTERVAL, default=defaults.get(CONF_HEALTH_PROMPT_INTERVAL, DEFAULT_HEALTH_PROMPT_INTERVAL)): selector.selector(
                {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
            ),
        }

        # ── Toggles — grouped together at the bottom ─────────────────────────
        # Notes toggle — always shown, options override takes priority over entry.data
        notes_currently_enabled = bool(
            current_opts.get(CONF_NOTES_ENABLED, entry.data.get(CONF_ENABLE_NOTES, False))
        )
        schema_fields[vol.Required(CONF_NOTES_ENABLED, default=notes_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )

        # Fertilization toggle — always shown unconditionally so users can enable
        # fertilization on plants that skipped it at setup.
        fert_currently_enabled = bool(
            current_opts.get(CONF_FERTILIZATION_ENABLED, entry.data.get(CONF_ENABLE_FERTILIZATION, False))
        )
        schema_fields[vol.Required(CONF_FERTILIZATION_ENABLED, default=fert_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )
        # Only show the interval field when fertilization is currently active
        if fert_currently_enabled:
            schema_fields[vol.Required(OPT_FERTILIZATION_INTERVAL, default=defaults.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL))] = selector.selector(
                {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
            )

        # Repotting toggle — always shown unconditionally.
        repotting_currently_enabled = bool(
            current_opts.get(CONF_REPOTTING_ENABLED, entry.data.get(CONF_ENABLE_REPOTTING, False))
        )
        schema_fields[vol.Required(CONF_REPOTTING_ENABLED, default=repotting_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )

        # Latin name toggle — always shown so users can enable it after setup.
        # If already enabled, also show the text field to edit the value.
        latin_currently_enabled = bool(
            current_opts.get(CONF_ENABLE_LATIN_NAME, entry.data.get(CONF_ENABLE_LATIN_NAME, False))
        )
        schema_fields[vol.Required(CONF_ENABLE_LATIN_NAME, default=latin_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )
        if latin_currently_enabled:
            # Use the same `defaults = {**entry.data, **current_opts}` lookup
            # pattern as CONF_LABEL and CONF_IMAGE_PATH so an empty-string
            # tombstone in options correctly shadows the entry.data value
            # instead of short-circuiting through an `or` fallback.
            current_latin = defaults.get(CONF_LATIN_NAME, "")
            schema_fields[
                vol.Optional(
                    CONF_LATIN_NAME,
                    description={"suggested_value": current_latin},
                )
            ] = selector.selector({"text": {}})

        # Image toggle — always shown so users can enable it after setup.
        # If already enabled, also show the path field to edit the value.
        image_currently_enabled = bool(
            current_opts.get(CONF_ENABLE_IMAGE, entry.data.get(CONF_ENABLE_IMAGE, False))
        )
        schema_fields[vol.Required(CONF_ENABLE_IMAGE, default=image_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )
        if image_currently_enabled:
            schema_fields[
                vol.Optional(
                    CONF_IMAGE_PATH,
                    description={"suggested_value": defaults.get(CONF_IMAGE_PATH, "")},
                )
            ] = selector.selector({"text": {}})

        # Moisture sensor toggle + picker — always shown
        has_moisture = bool(current_moisture)
        schema_fields[vol.Required("moisture_sensor_enabled", default=has_moisture)] = selector.selector(
            {"boolean": {}}
        )
        if current_moisture:
            sensor_field = vol.Optional(CONF_MOISTURE_SENSOR, default=current_moisture)
        else:
            sensor_field = vol.Optional(CONF_MOISTURE_SENSOR)
        schema_fields[sensor_field] = selector.selector(
            {"entity": {"domain": "sensor", "multiple": False}}
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    async def async_step_moisture_options(self, user_input: dict | None = None) -> FlowResult:
        """Second step shown only when a moisture sensor has been selected."""
        errors: dict[str, str] = {}
        entry = self._config_entry
        current_opts = entry.options
        defaults = {**entry.data, **current_opts}

        if user_input is not None:
            dry = user_input.get(CONF_DRY_THRESHOLD)
            wet = user_input.get(CONF_WET_THRESHOLD)
            if dry is not None and wet is not None and dry >= wet:
                errors["base"] = "dry_above_wet"
            else:
                merged = {
                    **current_opts,
                    **self._pending_opts,
                    CONF_MOISTURE_SENSOR: self._pending_moisture_sensor,
                    CONF_DRY_THRESHOLD: dry,
                    CONF_WET_THRESHOLD: wet,
                }

                # Apply label clear carried from step 1 — write an empty-string
                # tombstone rather than popping, so the PlantData.label
                # property's fallback to entry.data doesn't surface a stale
                # value set during the original setup wizard.
                if self._pending_clear_label:
                    merged[CONF_LABEL] = ""

                # ── First-enable detection (same as in async_step_init) ───────
                # Must run here too — when moisture options are collected first,
                # async_step_init never reaches the detection block in its else branch.
                fert_first_enable = (
                    self._pending_opts.get(CONF_FERTILIZATION_ENABLED) is True
                    and STATE_LAST_FERTILIZED not in current_opts
                )
                repot_first_enable = (
                    self._pending_opts.get(CONF_REPOTTING_ENABLED) is True
                    and STATE_LAST_REPOTTED not in current_opts
                )

                if fert_first_enable or repot_first_enable:
                    self._pending_opts = merged
                    self._pending_fert_first = fert_first_enable
                    self._pending_repot_first = repot_first_enable
                    if fert_first_enable:
                        return await self.async_step_fertilized_init()
                    return await self.async_step_repotted_init()

                return self.async_create_entry(title="", data=merged)

        return self.async_show_form(
            step_id="moisture_options",
            data_schema=_moisture_schema(defaults),
            errors=errors,
        )

    # ── Fertilization first-enable sub-flow ───────────────────────────────────

    async def async_step_fertilized_init(self, user_input: dict | None = None) -> FlowResult:
        """Ask when the plant was last fertilized — shown only on first enable."""
        if user_input is not None:
            selection = user_input[CONF_INITIAL_LAST_FERTILIZED]
            if selection == WATERING_DATE_CUSTOM:
                return await self.async_step_fertilized_init_custom()
            if selection != WATERING_DATE_NEVER:
                today = date.today()
                if selection == WATERING_DATE_TODAY:
                    last = today
                else:  # yesterday
                    last = today - timedelta(days=1)
                interval = int(
                    self._pending_opts.get(
                        OPT_FERTILIZATION_INTERVAL,
                        self._config_entry.options.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL),
                    )
                )
                self._pending_opts[STATE_LAST_FERTILIZED] = last.isoformat()
                self._pending_opts[STATE_NEXT_FERTILIZED] = (last + timedelta(days=interval)).isoformat()
            else:
                # "never" — strip any stale dates that may have been carried into merged
                self._pending_opts.pop(STATE_LAST_FERTILIZED, None)
                self._pending_opts.pop(STATE_NEXT_FERTILIZED, None)
            return await self._after_fertilized_init()
        return self.async_show_form(
            step_id="fertilized_init",
            data_schema=_last_fertilized_schema(),
        )

    async def async_step_fertilized_init_custom(self, user_input: dict | None = None) -> FlowResult:
        """Custom date entry for fertilization first-enable."""
        errors: dict[str, str] = {}
        if user_input is not None:
            custom_date = user_input.get("custom_fertilized_date", "")
            try:
                last = date.fromisoformat(custom_date)
            except ValueError:
                errors["custom_fertilized_date"] = "invalid_date"
            else:
                interval = int(
                    self._pending_opts.get(
                        OPT_FERTILIZATION_INTERVAL,
                        self._config_entry.options.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL),
                    )
                )
                self._pending_opts[STATE_LAST_FERTILIZED] = last.isoformat()
                self._pending_opts[STATE_NEXT_FERTILIZED] = (last + timedelta(days=interval)).isoformat()
                return await self._after_fertilized_init()
        return self.async_show_form(
            step_id="fertilized_init_custom",
            data_schema=_last_fertilized_custom_schema(),
            errors=errors,
        )

    async def _after_fertilized_init(self) -> FlowResult:
        """Route to repotting first-enable if also needed, otherwise save."""
        if self._pending_repot_first:
            return await self.async_step_repotted_init()
        return self.async_create_entry(title="", data=self._pending_opts)

    # ── Repotting first-enable sub-flow ───────────────────────────────────────

    async def async_step_repotted_init(self, user_input: dict | None = None) -> FlowResult:
        """Ask when the plant was last repotted — shown only on first enable."""
        if user_input is not None:
            selection = user_input[CONF_INITIAL_LAST_REPOTTED]
            if selection == WATERING_DATE_CUSTOM:
                return await self.async_step_repotted_init_custom()
            if selection != WATERING_DATE_NEVER:
                today = date.today()
                if selection == WATERING_DATE_TODAY:
                    last = today
                else:  # yesterday
                    last = today - timedelta(days=1)
                self._pending_opts[STATE_LAST_REPOTTED] = last.isoformat()
            else:
                # "never" — strip any stale date that may have been carried into merged
                self._pending_opts.pop(STATE_LAST_REPOTTED, None)
            return self.async_create_entry(title="", data=self._pending_opts)
        return self.async_show_form(
            step_id="repotted_init",
            data_schema=_last_repotted_schema(),
        )

    async def async_step_repotted_init_custom(self, user_input: dict | None = None) -> FlowResult:
        """Custom date entry for repotting first-enable."""
        errors: dict[str, str] = {}
        if user_input is not None:
            custom_date = user_input.get("custom_repotted_date", "")
            try:
                date.fromisoformat(custom_date)
            except ValueError:
                errors["custom_repotted_date"] = "invalid_date"
            else:
                self._pending_opts[STATE_LAST_REPOTTED] = custom_date
                return self.async_create_entry(title="", data=self._pending_opts)
        return self.async_show_form(
            step_id="repotted_init_custom",
            data_schema=_last_repotted_custom_schema(),
            errors=errors,
        )
