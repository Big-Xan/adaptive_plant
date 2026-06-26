"""Config flow for the Adaptive Plant integration."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import date, timedelta

import voluptuous as vol

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AREA,
    CONF_CARE_INSTRUCTIONS,
    CONF_DRY_THRESHOLD,
    CONF_EARLY_WATERING_THRESHOLD,
    CONF_ENABLE_CARE_INSTRUCTIONS,
    CONF_ENABLE_FERTILIZATION,
    CONF_ENABLE_IMAGE,
    CONF_ENABLE_LATIN_NAME,
    CONF_ENABLE_NOTES,
    CONF_ENABLE_REPOTTING,
    CONF_FERTILIZATION_ENABLED,
    CONF_HEALTH_PROMPT_INTERVAL,
    CONF_IMAGE_PATH,
    CONF_IMAGE_UPLOAD,
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
    DEFAULT_FERT_SYNC_WINDOW,
    DEFAULT_FERTILIZATION_INTERVAL,
    DEFAULT_HEALTH_PROMPT_INTERVAL,
    DEFAULT_SNOOZE_THRESHOLD,
    DEFAULT_WATERING_INTERVAL,
    DOMAIN,
    is_owned_image_path,
    OPT_FERTILIZATION_INTERVAL,
    OPT_FERT_SYNC_WINDOW,
    OPT_WATERING_INTERVAL,
    OWNED_IMAGE_PREFIX,
    STATE_LAST_FERTILIZED,
    STATE_LAST_REPOTTED,
    STATE_NEXT_FERTILIZED,
)

_LOGGER = logging.getLogger(__name__)

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
        vol.Required(OPT_FERT_SYNC_WINDOW, default=defaults.get(OPT_FERT_SYNC_WINDOW, DEFAULT_FERT_SYNC_WINDOW)): selector.selector(
            {"number": {"min": 0, "max": 6, "mode": "box", "unit_of_measurement": "days"}}
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
        vol.Optional(CONF_IMAGE_UPLOAD): selector.selector({"file": {"accept": "image/*"}}),
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


def _save_uploaded_image(hass: HomeAssistant, file_id: str, previous_path: str | None) -> str:
    """Blocking: read the uploaded file, downscale it, and write it to www/.

    Runs entirely inside an executor job — must not be awaited directly.
    """
    from PIL import Image

    target_dir = hass.config.path("www", DOMAIN)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    target_path = os.path.join(target_dir, filename)

    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass

    with process_uploaded_file(hass, file_id) as temp_path:
        with Image.open(temp_path) as img:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            img.save(target_path, format="JPEG", quality=85)

    if is_owned_image_path(previous_path):
        previous_filename = previous_path[len(OWNED_IMAGE_PREFIX):]
        previous_full_path = os.path.join(target_dir, previous_filename)
        try:
            os.remove(previous_full_path)
        except OSError:
            pass

    return f"{OWNED_IMAGE_PREFIX}{filename}"


def _delete_owned_image(hass: HomeAssistant, path: str) -> None:
    """Blocking: best-effort delete of an owned image file. Run in an executor job."""
    filename = path[len(OWNED_IMAGE_PREFIX):]
    full_path = os.path.join(hass.config.path("www", DOMAIN), filename)
    try:
        os.remove(full_path)
    except OSError:
        pass


async def _persist_uploaded_image(hass: HomeAssistant, file_id: str, previous_path: str | None) -> str:
    """Persist an uploaded image to www/adaptive_plant/ and return its public path.

    Raises on failure (corrupt/non-image upload) so callers can surface
    an `invalid_image` form error.
    """
    return await hass.async_add_executor_job(_save_uploaded_image, hass, file_id, previous_path)


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
            file_id = user_input.get(CONF_IMAGE_UPLOAD)
            path = user_input.get(CONF_IMAGE_PATH, "").strip()
            if file_id:
                try:
                    self._data[CONF_IMAGE_PATH] = await _persist_uploaded_image(
                        self.hass, file_id, self._data.get(CONF_IMAGE_PATH)
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Failed to process uploaded plant image")
                    errors[CONF_IMAGE_UPLOAD] = "invalid_image"
            elif path:
                if not path.startswith("/local/"):
                    errors[CONF_IMAGE_PATH] = "invalid_image_path"
                else:
                    self._data[CONF_IMAGE_PATH] = path
            else:
                self._data[CONF_IMAGE_PATH] = None

            if not errors:
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
        # Stash cleaned options while we run a sub-flow (fertilize/repot init).
        # _pending_opts holds ONLY the keys this flow is authoritative about this
        # run (settings the user edited, tombstones, first-enable dates). It is no
        # longer pre-merged with a snapshot of entry.options — _save() composes the
        # final dict against a fresh read at write time (see issue #23).
        self._pending_opts: dict = {}
        # Keys this flow deliberately *removes* this run (blanked settings,
        # cleared thresholds, "never" dates). _save() pops these off the fresh
        # base, but only when the flow didn't also set them this run.
        self._flow_removed_keys: set[str] = set()
        # Flags set when a first-enable sub-flow is in progress
        self._pending_image_first: bool = False
        self._pending_latin_first: bool = False
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
            # Fresh per submit — removal intent is rebuilt each run alongside
            # _pending_opts, so a re-shown form (e.g. after an image error) never
            # carries stale removals into the eventual save.
            self._flow_removed_keys = set()
            # Detect label-clear intent up front (blank, whitespace-only, or
            # the literal word "null"). The cleanup loop further down only
            # catches blanks AND only runs on the no-moisture branch, so we
            # need to capture intent here and apply it explicitly to `merged`
            # in both branches.
            raw_label = user_input.get(CONF_LABEL, "")
            label_stripped = raw_label.strip() if isinstance(raw_label, str) else ""
            clear_label = (not label_stripped) or label_stripped.lower() == "null"

            cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}
            cleaned.pop(CONF_IMAGE_UPLOAD, None)

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

            # Care instructions toggle — write the flag explicitly. The stored
            # text is preserved across a disable→enable cycle (like the fert and
            # repot dates), so a user can turn the section off and back on without
            # retyping their notes.
            #
            # The care text field is only rendered when care was ALREADY enabled
            # (see `care_currently_enabled` in the schema builder below), so we
            # overwrite the stored text only when care was on BOTH before and
            # after this submit — the one case where the field was shown and its
            # value, empty or not, is authoritative. Branching on the *stored*
            # state rather than key-presence is essential: HA drops an emptied
            # Optional text field (suggested_value, no default) from user_input
            # entirely, so a clear-while-enabled and a re-enable both arrive with
            # the key absent and must be told apart by something else. The old
            # `in user_input` guard conflated them and let the merge resurface
            # the stored value on clear. An explicit "" written here survives the
            # cleanup loop because CONF_CARE_INSTRUCTIONS is in _skip_clear. The
            # 2000-char cap is enforced here rather than on the text selector —
            # HA's TextSelector has no `max` key, so passing one 400s the form.
            care_was_enabled = bool(current_opts.get(CONF_ENABLE_CARE_INSTRUCTIONS, False))
            care_enabled = bool(user_input.get(CONF_ENABLE_CARE_INSTRUCTIONS, False))
            cleaned[CONF_ENABLE_CARE_INSTRUCTIONS] = care_enabled
            if care_enabled and care_was_enabled:
                raw_care = user_input.get(CONF_CARE_INSTRUCTIONS, "")
                cleaned[CONF_CARE_INSTRUCTIONS] = (raw_care or "")[:2000]

            # Image toggle — write explicitly, and handle the upload/text field.
            # Empty string is written as a tombstone (mirroring CONF_LABEL and
            # CONF_LATIN_NAME) so the PlantData.image_path property's fallback
            # to entry.data doesn't resurface a stale value set during the
            # original setup wizard.
            image_enabled = bool(user_input.get(CONF_ENABLE_IMAGE, False))
            cleaned[CONF_ENABLE_IMAGE] = image_enabled
            current_image_path = current_opts.get(CONF_IMAGE_PATH, entry.data.get(CONF_IMAGE_PATH))
            if image_enabled:
                upload_file_id = user_input.get(CONF_IMAGE_UPLOAD)
                if upload_file_id:
                    try:
                        cleaned[CONF_IMAGE_PATH] = await _persist_uploaded_image(
                            self.hass, upload_file_id, current_image_path
                        )
                    except Exception:  # noqa: BLE001
                        _LOGGER.exception("Failed to process uploaded plant image")
                        errors[CONF_IMAGE_UPLOAD] = "invalid_image"
                else:
                    raw_image = user_input.get(CONF_IMAGE_PATH, "")
                    new_path = raw_image.strip() if raw_image else ""
                    cleaned[CONF_IMAGE_PATH] = new_path
                    if new_path != current_image_path and is_owned_image_path(current_image_path):
                        await self.hass.async_add_executor_job(
                            _delete_owned_image, self.hass, current_image_path
                        )
            else:
                # Image disabled — tombstone the path (mirroring CONF_LABEL /
                # CONF_LATIN_NAME) rather than popping. We also delete the owned
                # file below, so a bare pop would leave a stale path in options
                # that resurfaces as a broken image if the user re-enables
                # without re-uploading. The "" tombstone is preserved through
                # `merged` by _skip_clear and makes image_path resolve to None.
                cleaned[CONF_IMAGE_PATH] = ""
                if is_owned_image_path(current_image_path):
                    await self.hass.async_add_executor_job(
                        _delete_owned_image, self.hass, current_image_path
                    )

            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema(self._init_schema_fields()),
                    errors=errors,
                )

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
                # Carry non-moisture fields forward so they're saved with the thresholds.
                self._pending_opts = cleaned
                # Carry the clear-label intent forward — step 2's merge would
                # otherwise pull the stale value back in from current_opts.
                self._pending_clear_label = clear_label
                # Dry/wet thresholds are shown inline on the main form whenever a
                # sensor is already active (see _init_schema_fields), so they can be
                # edited on demand and saved in one step. They are absent only on a
                # first-time enable — the form was built with the sensor off, so the
                # fields couldn't be shown — in which case we collect them once in the
                # dedicated step.
                inline_dry = user_input.get(CONF_DRY_THRESHOLD)
                inline_wet = user_input.get(CONF_WET_THRESHOLD)
                if inline_dry is not None and inline_wet is not None:
                    if inline_dry >= inline_wet:
                        return self.async_show_form(
                            step_id="init",
                            data_schema=vol.Schema(self._init_schema_fields()),
                            errors={"base": "dry_above_wet"},
                        )
                    return await self.async_step_moisture_options(
                        {CONF_DRY_THRESHOLD: inline_dry, CONF_WET_THRESHOLD: inline_wet}
                    )
                return await self.async_step_moisture_options()
            else:
                # Sensor cleared — tombstone the sensor and strip thresholds.
                # The sensor key gets an empty-string tombstone (not a removal)
                # because PlantData.moisture_sensor falls back to entry.data
                # when the key is missing — removing it would resurrect a sensor
                # chosen during the original setup wizard. The thresholds are
                # removed from the fresh base in _save(): every moisture code
                # path gates on moisture_sensor first, so their entry.data
                # fallback is inert.
                cleaned[CONF_MOISTURE_SENSOR] = ""
                cleaned.pop(CONF_DRY_THRESHOLD, None)
                cleaned.pop(CONF_WET_THRESHOLD, None)
                self._flow_removed_keys.add(CONF_DRY_THRESHOLD)
                self._flow_removed_keys.add(CONF_WET_THRESHOLD)
                # Explicit label clear — write an empty-string tombstone rather
                # than removing the key. The PlantData.label property falls
                # back to entry.data when CONF_LABEL is missing from options,
                # so a removal leaves a stale value from setup visible. An empty
                # string in options is treated as "cleared" by the property
                # and shadows the entry.data fallback.
                if clear_label:
                    cleaned[CONF_LABEL] = ""
                # Also clear blanked fields — but skip keys we've already
                # handled explicitly above. Tombstone keys (CONF_LABEL,
                # CONF_LATIN_NAME, CONF_IMAGE_PATH, CONF_MOISTURE_SENSOR) are
                # included because their empty-string tombstones are intentional
                # — without the skip they would be marked for removal and the
                # fresh base would fall back to stale entry.data values from the
                # original setup wizard. Blanked non-skip keys become removal
                # intent for _save() rather than a delete off a stale snapshot.
                _skip_clear = {
                    CONF_LABEL,
                    CONF_LATIN_NAME,
                    CONF_IMAGE_PATH,
                    CONF_MOISTURE_SENSOR,
                    CONF_NOTES_ENABLED,
                    CONF_ENABLE_LATIN_NAME,
                    CONF_CARE_INSTRUCTIONS,
                    CONF_ENABLE_CARE_INSTRUCTIONS,
                    CONF_FERTILIZATION_ENABLED,
                    CONF_REPOTTING_ENABLED,
                    CONF_ENABLE_IMAGE,
                }
                for k, v in user_input.items():
                    if k not in _skip_clear and v in (None, ""):
                        self._flow_removed_keys.add(k)

                # ── First-enable detection ────────────────────────────────────
                # Each fires when its toggle flips on in this save and the
                # feature wasn't already active, so the matching sub-step can
                # collect the missing input (image path, latin name, dates) in
                # the same flow — mirroring the setup wizard. Without this, a
                # dependent field can't appear until the form is reopened, since
                # an options-flow schema is built once before the user toggles.
                image_was_enabled = bool(
                    current_opts.get(CONF_ENABLE_IMAGE, entry.data.get(CONF_ENABLE_IMAGE, False))
                )
                latin_was_enabled = bool(
                    current_opts.get(CONF_ENABLE_LATIN_NAME, entry.data.get(CONF_ENABLE_LATIN_NAME, False))
                )
                fertilization_was_enabled = bool(
                    current_opts.get(CONF_FERTILIZATION_ENABLED, entry.data.get(CONF_ENABLE_FERTILIZATION, False))
                )
                repotting_was_enabled = bool(
                    current_opts.get(CONF_REPOTTING_ENABLED, entry.data.get(CONF_ENABLE_REPOTTING, False))
                )
                self._pending_opts = cleaned
                self._pending_image_first = (
                    cleaned.get(CONF_ENABLE_IMAGE) is True and not image_was_enabled
                )
                self._pending_latin_first = (
                    cleaned.get(CONF_ENABLE_LATIN_NAME) is True and not latin_was_enabled
                )
                # Fertilization: toggle flipped on this save, wasn't already active, and no date yet.
                # The not-already-active guard mirrors the image/latin gates above; without it any
                # later edit re-fires this sub-step while a date is genuinely absent (e.g. "never
                # fertilized"), and a preserved date survives a disable→enable cycle untouched.
                self._pending_fert_first = (
                    cleaned.get(CONF_FERTILIZATION_ENABLED) is True
                    and not fertilization_was_enabled
                    and STATE_LAST_FERTILIZED not in current_opts
                )
                # Repotting: same three-part guard as fertilization.
                self._pending_repot_first = (
                    cleaned.get(CONF_REPOTTING_ENABLED) is True
                    and not repotting_was_enabled
                    and STATE_LAST_REPOTTED not in current_opts
                )

                return await self._route_first_enable()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(self._init_schema_fields()),
            errors=errors,
        )

    def _init_schema_fields(self) -> dict:
        """Build the field dict for the `init` step schema (also used to re-show on error)."""
        entry = self._config_entry
        current_opts = entry.options
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
            schema_fields[vol.Required(OPT_FERT_SYNC_WINDOW, default=defaults.get(OPT_FERT_SYNC_WINDOW, DEFAULT_FERT_SYNC_WINDOW))] = selector.selector(
                {"number": {"min": 0, "max": 6, "mode": "box", "unit_of_measurement": "days"}}
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

        # Care instructions toggle — always shown so users can enable it after
        # setup. If enabled, show a multiline text box (markdown-ish: **bold**).
        care_currently_enabled = bool(
            current_opts.get(CONF_ENABLE_CARE_INSTRUCTIONS, False)
        )
        schema_fields[vol.Required(CONF_ENABLE_CARE_INSTRUCTIONS, default=care_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )
        if care_currently_enabled:
            schema_fields[
                vol.Optional(
                    CONF_CARE_INSTRUCTIONS,
                    description={"suggested_value": defaults.get(CONF_CARE_INSTRUCTIONS, "")},
                )
            ] = selector.selector({"text": {"multiline": True}})

        # Image toggle — always shown so users can enable it after setup.
        # If already enabled, also show the path field to edit the value.
        image_currently_enabled = bool(
            current_opts.get(CONF_ENABLE_IMAGE, entry.data.get(CONF_ENABLE_IMAGE, False))
        )
        schema_fields[vol.Required(CONF_ENABLE_IMAGE, default=image_currently_enabled)] = selector.selector(
            {"boolean": {}}
        )
        if image_currently_enabled:
            schema_fields[vol.Optional(CONF_IMAGE_UPLOAD)] = selector.selector(
                {"file": {"accept": "image/*"}}
            )
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

        # When a sensor is already active, show its dry/wet thresholds inline so
        # they can be edited here on demand. The dedicated threshold step is then
        # only needed for a first-time sensor enable (the form is built once, so a
        # sensor toggled on in THIS submission can't reveal these fields yet).
        # Same selector spec as _moisture_schema.
        if current_moisture:
            schema_fields[
                vol.Required(CONF_DRY_THRESHOLD, default=defaults.get(CONF_DRY_THRESHOLD, 30.0))
            ] = selector.selector({"number": {"min": 0, "max": 100, "step": 0.1, "mode": "box"}})
            schema_fields[
                vol.Required(CONF_WET_THRESHOLD, default=defaults.get(CONF_WET_THRESHOLD, 70.0))
            ] = selector.selector({"number": {"min": 0, "max": 100, "step": 0.1, "mode": "box"}})

        return schema_fields

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
                # Overlay the sensor + thresholds onto the flow-owned dict
                # carried from step 1 (cleaned). No snapshot base here — _save()
                # composes against a fresh read of entry.options at write time
                # (issue #23), so runtime keys survive any gap before the save.
                self._pending_opts = {
                    **self._pending_opts,
                    CONF_MOISTURE_SENSOR: self._pending_moisture_sensor,
                    CONF_DRY_THRESHOLD: dry,
                    CONF_WET_THRESHOLD: wet,
                }

                # Apply label clear carried from step 1 — write an empty-string
                # tombstone rather than removing, so the PlantData.label
                # property's fallback to entry.data doesn't surface a stale
                # value set during the original setup wizard.
                if self._pending_clear_label:
                    self._pending_opts[CONF_LABEL] = ""

                # ── First-enable detection (same as in async_step_init) ───────
                # Must run here too — when moisture options are collected first,
                # async_step_init never reaches the detection block in its else branch.
                image_was_enabled = bool(
                    current_opts.get(CONF_ENABLE_IMAGE, entry.data.get(CONF_ENABLE_IMAGE, False))
                )
                latin_was_enabled = bool(
                    current_opts.get(CONF_ENABLE_LATIN_NAME, entry.data.get(CONF_ENABLE_LATIN_NAME, False))
                )
                fertilization_was_enabled = bool(
                    current_opts.get(CONF_FERTILIZATION_ENABLED, entry.data.get(CONF_ENABLE_FERTILIZATION, False))
                )
                repotting_was_enabled = bool(
                    current_opts.get(CONF_REPOTTING_ENABLED, entry.data.get(CONF_ENABLE_REPOTTING, False))
                )
                self._pending_image_first = (
                    self._pending_opts.get(CONF_ENABLE_IMAGE) is True and not image_was_enabled
                )
                self._pending_latin_first = (
                    self._pending_opts.get(CONF_ENABLE_LATIN_NAME) is True and not latin_was_enabled
                )
                self._pending_fert_first = (
                    self._pending_opts.get(CONF_FERTILIZATION_ENABLED) is True
                    and not fertilization_was_enabled
                    and STATE_LAST_FERTILIZED not in current_opts
                )
                self._pending_repot_first = (
                    self._pending_opts.get(CONF_REPOTTING_ENABLED) is True
                    and not repotting_was_enabled
                    and STATE_LAST_REPOTTED not in current_opts
                )

                return await self._route_first_enable()

        return self.async_show_form(
            step_id="moisture_options",
            data_schema=_moisture_schema(defaults),
            errors=errors,
        )

    # ── Single save chokepoint ────────────────────────────────────────────────

    def _save(self) -> FlowResult:
        """Write options through one chokepoint that composes against a fresh read.

        Issue #23: the options flow used to snapshot entry.options early and save
        that snapshot at the end, so any PlantData._persist() write landing in
        between (a Mark Watered/Fertilized/Repotted, a health/notes edit, a
        moisture-driven reschedule) was silently lost. Here the fresh, current
        options are the base and _pending_opts overlays only the keys this flow
        is authoritative about this run — so untouched runtime state can never be
        clobbered. _flow_removed_keys carries deliberate removals (cleared
        thresholds, blanked settings, "never" dates); a key the flow both removed
        and set in the same run keeps its set value (the `not in _pending_opts`
        guard). No new runtime key needs registering here: anything the flow
        doesn't touch is preserved from the fresh base by default.
        """
        fresh = dict(self._config_entry.options)
        final = {**fresh, **self._pending_opts}
        for key in self._flow_removed_keys:
            if key not in self._pending_opts:
                final.pop(key, None)
        return self.async_create_entry(title="", data=final)

    # ── First-enable sub-flow dispatcher ──────────────────────────────────────

    async def _route_first_enable(self) -> FlowResult:
        """Route to the next pending first-enable sub-step, or save.

        Ordered image → latin → fertilization → repotting. The image/latin steps
        clear their own flag and call back here; the fertilization/repotting
        steps retain their existing chain (_after_fertilized_init → repot →
        save), so this dispatcher only fronts the chain and leaves that logic
        untouched. When no flag is set, the merged options are written via _save().
        """
        if self._pending_image_first:
            return await self.async_step_image_init()
        if self._pending_latin_first:
            return await self.async_step_latin_init()
        if self._pending_fert_first:
            return await self.async_step_fertilized_init()
        if self._pending_repot_first:
            return await self.async_step_repotted_init()
        return self._save()

    async def async_step_image_init(self, user_input: dict | None = None) -> FlowResult:
        """Ask for the image (upload or path) on first enable via options — mirrors setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            file_id = user_input.get(CONF_IMAGE_UPLOAD)
            path = user_input.get(CONF_IMAGE_PATH, "").strip()
            if file_id:
                # Upload wins over a typed path, matching the setup wizard and
                # the steady-state options form. previous_path is read from the
                # live entry so a prior owned file is cleaned up; on a genuine
                # first-enable it is normally absent.
                entry = self._config_entry
                previous_path = entry.options.get(
                    CONF_IMAGE_PATH, entry.data.get(CONF_IMAGE_PATH)
                )
                try:
                    self._pending_opts[CONF_IMAGE_PATH] = await _persist_uploaded_image(
                        self.hass, file_id, previous_path
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Failed to process uploaded plant image")
                    errors[CONF_IMAGE_UPLOAD] = "invalid_image"
            elif path:
                if not path.startswith("/local/"):
                    errors[CONF_IMAGE_PATH] = "invalid_image_path"
                else:
                    self._pending_opts[CONF_IMAGE_PATH] = path
            else:
                # Empty-string tombstone (mirrors the inline image handling) so
                # the PlantData.image_path fallback to entry.data can't resurface
                # a stale setup-wizard value.
                self._pending_opts[CONF_IMAGE_PATH] = ""

            if not errors:
                self._pending_image_first = False
                return await self._route_first_enable()
        return self.async_show_form(
            step_id="image_init",
            data_schema=_image_schema({}),
            errors=errors,
        )

    async def async_step_latin_init(self, user_input: dict | None = None) -> FlowResult:
        """Ask for the latin name on first enable via options — mirrors setup."""
        if user_input is not None:
            name = user_input.get(CONF_LATIN_NAME, "").strip()
            self._pending_opts[CONF_LATIN_NAME] = name or ""
            self._pending_latin_first = False
            return await self._route_first_enable()
        return self.async_show_form(
            step_id="latin_init",
            data_schema=_latin_name_schema({}),
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
                # "never" — ensure no fertilization dates are written. Remove
                # any flow-set value and record removal intent so _save() also
                # strips a date present on the fresh base (defensive: on a true
                # first-enable the fert entities don't exist yet, so none should
                # be there, but this keeps "never" authoritative regardless).
                self._pending_opts.pop(STATE_LAST_FERTILIZED, None)
                self._pending_opts.pop(STATE_NEXT_FERTILIZED, None)
                self._flow_removed_keys.add(STATE_LAST_FERTILIZED)
                self._flow_removed_keys.add(STATE_NEXT_FERTILIZED)
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
        return self._save()

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
                # "never" — ensure no repot date is written. Remove any flow-set
                # value and record removal intent so _save() also strips a date on
                # the fresh base (defensive; mirrors the fertilization "never" path).
                self._pending_opts.pop(STATE_LAST_REPOTTED, None)
                self._flow_removed_keys.add(STATE_LAST_REPOTTED)
            return self._save()
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
                return self._save()
        return self.async_show_form(
            step_id="repotted_init_custom",
            data_schema=_last_repotted_custom_schema(),
            errors=errors,
        )
