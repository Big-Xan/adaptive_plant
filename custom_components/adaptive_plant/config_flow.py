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
    CONF_HEALTH_PROMPT_INTERVAL,
    CONF_IMAGE_PATH,
    CONF_INITIAL_LAST_FERTILIZED,
    CONF_INITIAL_LAST_WATERED,
    CONF_LABEL,
    CONF_LATIN_NAME,
    CONF_MOISTURE_SENSOR,
    CONF_NOTES_ENABLED,
    CONF_PLANT_NAME,
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
)

WATERING_DATE_TODAY = "today"
WATERING_DATE_YESTERDAY = "yesterday"
WATERING_DATE_CUSTOM = "custom"
WATERING_DATE_NEVER = "never"


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

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self._config_entry
        current_opts = entry.options

        if user_input is not None:
            cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}

            # Normalise label
            if CONF_LABEL in cleaned:
                lv = cleaned[CONF_LABEL].strip()
                if not lv or lv.lower() == "null":
                    del cleaned[CONF_LABEL]
                else:
                    cleaned[CONF_LABEL] = lv

            # Notes enabled toggle — always write explicitly so falsy value persists
            cleaned[CONF_NOTES_ENABLED] = bool(user_input.get(CONF_NOTES_ENABLED, False))

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
                return await self.async_step_moisture_options()
            else:
                # Sensor cleared — strip moisture-related keys from options
                merged = {**current_opts, **cleaned}
                for key in (CONF_MOISTURE_SENSOR, CONF_DRY_THRESHOLD, CONF_WET_THRESHOLD):
                    merged.pop(key, None)
                # Also clear blanked fields — but skip keys we've already
                # handled explicitly above (boolean toggles that are legitimately false)
                _skip_clear = {CONF_NOTES_ENABLED, CONF_ENABLE_LATIN_NAME}
                for k, v in user_input.items():
                    if k not in _skip_clear and v in (None, "") and k in merged:
                        del merged[k]
                return self.async_create_entry(title="", data=merged)

        defaults = {**entry.data, **current_opts}

        # Resolve the currently active moisture sensor (options take priority)
        current_moisture = (
            current_opts.get(CONF_MOISTURE_SENSOR)
            or entry.data.get(CONF_MOISTURE_SENSOR)
            or None
        )

        schema_fields: dict = {
            vol.Optional(CONF_LABEL, default=defaults.get(CONF_LABEL, "")): selector.selector(
                {"text": {}}
            ),
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

        if entry.data.get(CONF_ENABLE_FERTILIZATION):
            schema_fields[vol.Required(OPT_FERTILIZATION_INTERVAL, default=defaults.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL))] = selector.selector(
                {"number": {"min": 1, "max": 365, "mode": "box", "unit_of_measurement": "days"}}
            )

        if entry.data.get(CONF_ENABLE_IMAGE):
            schema_fields[vol.Optional(CONF_IMAGE_PATH, default=defaults.get(CONF_IMAGE_PATH, ""))] = selector.selector(
                {"text": {}}
            )

        # ── Toggles — grouped together at the bottom ─────────────────────────
        # Notes toggle — always shown, options override takes priority over entry.data
        notes_currently_enabled = bool(
            current_opts.get(CONF_NOTES_ENABLED, entry.data.get(CONF_ENABLE_NOTES, False))
        )
        schema_fields[vol.Required(CONF_NOTES_ENABLED, default=notes_currently_enabled)] = selector.selector(
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
            current_latin = current_opts.get(CONF_LATIN_NAME) or entry.data.get(CONF_LATIN_NAME, "")
            schema_fields[vol.Optional(CONF_LATIN_NAME, default=current_latin)] = selector.selector(
                {"text": {}}
            )

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
                return self.async_create_entry(title="", data=merged)

        return self.async_show_form(
            step_id="moisture_options",
            data_schema=_moisture_schema(defaults),
            errors=errors,
        )
