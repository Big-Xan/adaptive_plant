"""Adaptive Plant integration — entry point."""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import (
    CONF_AREA,
    CONF_IMAGE_PATH,
    DEFAULT_HEALTH,
    DOMAIN,
    HEALTH_OPTIONS,
    is_owned_image_path,
    OPT_WATERING_INTERVAL,
    PLATFORMS,
    STATE_HEALTH,
    STATE_HEALTH_LAST_UPDATED,
    STATE_LAST_FERTILIZED,
    STATE_LAST_REPOTTED,
    STATE_LAST_WATERED,
    STATE_NEXT_FERTILIZED,
    STATE_NEXT_WATERING,
)
from .images import MIGRATED, MISSING, delete_owned_image, migrate_legacy_image
from .plant import PlantData, local_today
from .repairs import async_check_public_photos
from .sensor import moisture_entity_wanted

_LOGGER = logging.getLogger(__name__)

_CARD_URL = f"/{DOMAIN}/adaptive-plant-card.js"
_CARD_PATH = Path(__file__).parent / "frontend" / "adaptive-plant-card.js"
_BLUEPRINTS_SRC = Path(__file__).parent / "blueprints" / "automation"

# sha256 of every version of each bundled blueprint that has ever shipped
# (including the pre-1.2.0 copies users installed by hand). An installed file
# matching one of these is an unmodified stock copy and may be updated; any
# other content is the user's edit and is never touched. When a blueprint
# changes, add the hash of the version being replaced here.
_SHIPPED_BLUEPRINT_SHA256: dict[str, frozenset[str]] = {
    "plant_task_reminders.yaml": frozenset({
        "75e093645fafd52fe8058943c373c192f2caf7e9bd4c3dbb0581dc6ec7355166",  # v1.0.3
        "3172c0648de7247f22d4847c1f8dd1671b284e84fa2f6499d33058f11a18fe0a",  # v1.0.5
        "1fc66055e2ba13c5704a6d213af2bb26ed33ee66ed1084da0e79f447f2e8f089",  # v1.2.0 – v1.2.4
    }),
}


def _entity_features(hass: HomeAssistant, entry: ConfigEntry, plant: PlantData) -> dict[str, bool]:
    """Features whose entities are only created when the platforms set up."""
    return {
        "fertilization": plant.enable_fertilization,
        "notes": plant.enable_notes,
        "latin_name": plant.enable_latin_name,
        "repotting": plant.enable_repotting,
        "moisture": moisture_entity_wanted(hass, entry, plant),
        "image": plant.enable_image,
    }


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the card as a static path and Lovelace resource (once per HA run)."""
    from homeassistant.components.http import StaticPathConfig

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path=_CARD_URL, path=str(_CARD_PATH), cache_headers=False)]
        )
    except RuntimeError:
        # Route already registered from a previous setup call — safe to ignore
        pass

    # Auto-register as a Lovelace resource in storage mode.
    # Silently skips if Lovelace is in YAML mode.
    try:
        lovelace = hass.data.get("lovelace")
        # Older HA (incl. the 2024.7 floor) keeps a dict here; newer HA an
        # object with a .resources attribute. In YAML mode there is no
        # storage collection to add to.
        if isinstance(lovelace, dict):
            resources = lovelace.get("resources")
        else:
            resources = getattr(lovelace, "resources", None)
        if resources is not None and hasattr(resources, "async_create_item"):
            await resources.async_load()
            already_registered = any(
                _CARD_URL in (item.get("url") or "")
                for item in resources.async_items()
            )
            if not already_registered:
                await resources.async_create_item(
                    {"res_type": "module", "url": _CARD_URL}
                )
    except Exception:  # noqa: BLE001
        _LOGGER.debug(
            "Lovelace resource auto-registration skipped "
            "(YAML mode or Lovelace not yet loaded)"
        )


def _copy_blueprints(config_path: str) -> None:
    """Install bundled blueprints into the HA blueprints directory (executor job).

    A blueprint is written only when the installed copy is missing or is an
    unmodified copy of a version we shipped; a user-edited copy is never
    replaced, whatever its modification time (HACS gives every file in a
    release a fresh one). The write goes to a temp file renamed into place, so
    an interrupted copy can't leave a half-written blueprint behind.
    """
    dst_dir = Path(config_path) / "blueprints" / "automation" / DOMAIN
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src_file in _BLUEPRINTS_SRC.glob("*.yaml"):
        dst_file = dst_dir / src_file.name
        content = src_file.read_bytes()
        if dst_file.exists():
            installed = dst_file.read_bytes()
            if installed == content:
                continue
            shipped = _SHIPPED_BLUEPRINT_SHA256.get(src_file.name, frozenset())
            if hashlib.sha256(installed).hexdigest() not in shipped:
                _LOGGER.debug("Keeping edited blueprint %s", dst_file)
                continue
        fd, tmp = tempfile.mkstemp(dir=dst_dir, prefix=f".{src_file.name}.", suffix=".part")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
            os.replace(tmp, dst_file)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        _LOGGER.debug("Installed blueprint %s → %s", src_file.name, dst_file)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Adaptive Plant config entry."""
    hass.data.setdefault(DOMAIN, {})

    # ── Frontend card + Lovelace resource (once per HA run) ──────────────────
    if not hass.data.get(f"{DOMAIN}_frontend_registered"):
        await _async_register_frontend(hass)
        hass.data[f"{DOMAIN}_frontend_registered"] = True

    # ── Blueprints (copy with mtime guard, executor) ─────────────────────────
    if not hass.data.get(f"{DOMAIN}_blueprints_copied"):
        # A disk error here (read-only or full config folder) must not stop the
        # plant from loading: the blueprint is optional. Not marked as copied,
        # so the next plant setup tries again.
        try:
            await hass.async_add_executor_job(_copy_blueprints, hass.config.config_dir)
        except OSError as err:
            _LOGGER.warning("Could not copy the Adaptive Plant blueprint: %s", err)
        else:
            hass.data[f"{DOMAIN}_blueprints_copied"] = True

    # ── Seed initial state from setup wizard on first load ───────────────────
    initial_options: dict = dict(entry.options)
    seeded = False

    last_watered = entry.data.get("_resolved_last_watered")
    next_watering = entry.data.get("_resolved_next_watering")
    if next_watering and STATE_NEXT_WATERING not in initial_options:
        if last_watered:
            initial_options[STATE_LAST_WATERED] = last_watered
        initial_options[STATE_NEXT_WATERING] = next_watering
        seeded = True

    last_fertilized = entry.data.get("_resolved_last_fertilized")
    next_fertilized = entry.data.get("_resolved_next_fertilized")
    if next_fertilized and STATE_NEXT_FERTILIZED not in initial_options:
        if last_fertilized:
            initial_options[STATE_LAST_FERTILIZED] = last_fertilized
        initial_options[STATE_NEXT_FERTILIZED] = next_fertilized
        seeded = True

    resolved_last_repotted = entry.data.get("_resolved_last_repotted")
    if resolved_last_repotted and STATE_LAST_REPOTTED not in initial_options:
        initial_options[STATE_LAST_REPOTTED] = resolved_last_repotted
        seeded = True

    if OPT_WATERING_INTERVAL not in initial_options and OPT_WATERING_INTERVAL in entry.data:
        initial_options[OPT_WATERING_INTERVAL] = entry.data[OPT_WATERING_INTERVAL]
        seeded = True

    if STATE_HEALTH_LAST_UPDATED not in initial_options:
        initial_options[STATE_HEALTH_LAST_UPDATED] = local_today().isoformat()
        seeded = True

    current_health = initial_options.get(STATE_HEALTH)
    if current_health not in HEALTH_OPTIONS:
        initial_options[STATE_HEALTH] = DEFAULT_HEALTH
        seeded = True

    if seeded:
        hass.config_entries.async_update_entry(entry, options=initial_options)

    # ── Move a 1.2.4-era uploaded photo out of www/ (before entities exist) ──
    # The reference in the entry is unchanged; only the file moves to private
    # storage, so its old /local/ URL stops serving it. Retried on every setup
    # until it succeeds.
    image_path = entry.options.get(CONF_IMAGE_PATH, entry.data.get(CONF_IMAGE_PATH))
    if is_owned_image_path(image_path):
        try:
            result = await hass.async_add_executor_job(
                migrate_legacy_image, hass.config.config_dir, image_path
            )
        except OSError as err:
            _LOGGER.warning(
                "%s: could not move the plant photo out of www/%s (will retry at "
                "next start): %s", entry.title, DOMAIN, err,
            )
        else:
            if result == MISSING:
                _LOGGER.warning(
                    "%s: the uploaded plant photo is missing; upload it again in "
                    "Configure", entry.title,
                )
            elif result == MIGRATED:
                _LOGGER.info("%s: moved the plant photo to private storage", entry.title)

    # Once per HA run: flag uploads left public in www/ that no plant uses
    # (Repairs; the user decides whether to delete them).
    if not hass.data.get(f"{DOMAIN}_photo_check_done"):
        hass.data[f"{DOMAIN}_photo_check_done"] = True
        await async_check_public_photos(hass)

    plant = PlantData(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = plant

    # Seasonal schedule (Experimental): bring the plant in line with the season
    # active today before the entities come up. Covers startup, Reload, a new
    # plant created with seasons, and HA having been off across a boundary.
    await plant.apply_seasons()

    # The wizard's area choice is applied ONCE, when the device is first
    # created (suggested-area semantics). Capture existence before platform
    # setup: the device registry is persistent, so a device found here means
    # this is not the entry's first-ever load and the user's current area
    # assignment (including a deliberately cleared one) must be respected —
    # re-applying entry.data's snapshot on every load reverts area changes
    # made on the device page.
    # Which optional entities this setup creates. Turning one of these features
    # on later needs a reload to create its entities (see the options listener).
    created_features = _entity_features(hass, entry, plant)

    dev_reg = dr.async_get(hass)
    device_preexisting = bool(
        dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Startup moisture check ───────────────────────────────────────────────
    async def _startup_moisture_check() -> None:
        await plant.startup_moisture_check()

    hass.async_create_task(_startup_moisture_check())

    # ── Assign device to area on first creation only ─────────────────────────
    area_id: str | None = entry.data.get(CONF_AREA)
    if area_id and not device_preexisting:
        devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        if devices:
            dev_reg.async_update_device(devices[0].id, area_id=area_id)

    # ── Daily rollover at 00:05 ──────────────────────────────────────────────
    async def _daily_rollover(now):
        await plant.daily_rollover()

    entry.async_on_unload(
        async_track_time_change(hass, _daily_rollover, hour=0, minute=5, second=0)
    )

    # ── Moisture sensor listener ─────────────────────────────────────────────
    _moisture_unsub = None

    def _register_moisture_listener() -> None:
        nonlocal _moisture_unsub
        if _moisture_unsub is not None:
            _moisture_unsub()
            _moisture_unsub = None

        # Seed (or reset) the auto-mark baseline before subscribing, so the
        # first state change is compared against a real reading.
        plant.seed_moisture_baseline()

        sensor_id: str | None = plant.moisture_sensor
        if not sensor_id:
            return

        async def _moisture_state_changed(event: Event) -> None:
            new_state = event.data.get("new_state")
            if new_state is not None and new_state.state not in ("unknown", "unavailable"):
                await plant.handle_moisture_change(new_state.state)

        _moisture_unsub = async_track_state_change_event(
            hass, [sensor_id], _moisture_state_changed
        )

    _register_moisture_listener()

    # ── Options update listener ──────────────────────────────────────────────
    async def _handle_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
        # A feature switched on after setup (fertilization, notes, latin name,
        # repotting, or a moisture sensor linked to a plant without a Soil
        # moisture entity) has no entities yet: reload once to create them.
        # Only these changes reload. Watering, notes text and every other
        # runtime write also land here, but never switch a feature on.
        wanted = _entity_features(hass, entry, plant)
        if any(on and not created_features[key] for key, on in wanted.items()):
            _LOGGER.debug("%s: feature enabled — reloading to create its entities", plant.plant_name)
            hass.config_entries.async_schedule_reload(entry.entry_id)
            return
        _register_moisture_listener()
        # Apply a season table saved in Configure (or an active season's
        # interval edited there) right away. Idempotent: on any other options
        # write it finds nothing to change, so it never loops.
        await plant.apply_seasons()
        plant._notify_listeners()

    entry.async_on_unload(entry.add_update_listener(_handle_options_update))

    def _unsub_moisture() -> None:
        if _moisture_unsub is not None:
            _moisture_unsub()

    entry.async_on_unload(_unsub_moisture)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Adaptive Plant config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up an owned uploaded image when the config entry is removed."""
    image_path = entry.options.get(CONF_IMAGE_PATH, entry.data.get(CONF_IMAGE_PATH))
    if is_owned_image_path(image_path):
        await hass.async_add_executor_job(delete_owned_image, hass.config.config_dir, image_path)
