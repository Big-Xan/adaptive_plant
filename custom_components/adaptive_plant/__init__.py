"""Adaptive Plant integration — entry point."""
from __future__ import annotations

import logging
import shutil
from datetime import date
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
    CONF_MOISTURE_SENSOR,
    DEFAULT_HEALTH,
    DOMAIN,
    HEALTH_OPTIONS,
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
from .plant import PlantData

_LOGGER = logging.getLogger(__name__)

_CARD_URL = f"/{DOMAIN}/adaptive-plant-card.js"
_CARD_PATH = Path(__file__).parent / "frontend" / "adaptive-plant-card.js"
_BLUEPRINTS_SRC = Path(__file__).parent / "blueprints" / "automation"


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the card as a static path and Lovelace resource (once per HA run)."""
    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url_path=_CARD_URL, path=str(_CARD_PATH), cache_headers=False)]
    )

    # Auto-register as a Lovelace resource in storage mode.
    # Silently skips if Lovelace is in YAML mode.
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace and hasattr(lovelace, "resources"):
            resources = lovelace.resources
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
    """Copy bundled blueprints into the HA blueprints directory (executor job)."""
    dst_dir = Path(config_path) / "blueprints" / "automation" / DOMAIN
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src_file in _BLUEPRINTS_SRC.glob("*.yaml"):
        dst_file = dst_dir / src_file.name
        # mtime guard — skip if destination is newer (preserves user edits)
        if dst_file.exists() and dst_file.stat().st_mtime >= src_file.stat().st_mtime:
            continue
        shutil.copy2(src_file, dst_file)
        _LOGGER.debug("Copied blueprint %s → %s", src_file.name, dst_file)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Adaptive Plant config entry."""
    hass.data.setdefault(DOMAIN, {})

    # ── Frontend card + Lovelace resource (once per HA run) ──────────────────
    if not hass.data[DOMAIN].get("_frontend_registered"):
        await _async_register_frontend(hass)
        hass.data[DOMAIN]["_frontend_registered"] = True

    # ── Blueprints (copy with mtime guard, executor) ─────────────────────────
    if not hass.data[DOMAIN].get("_blueprints_copied"):
        await hass.async_add_executor_job(_copy_blueprints, hass.config.config_dir)
        hass.data[DOMAIN]["_blueprints_copied"] = True

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
        initial_options[STATE_HEALTH_LAST_UPDATED] = date.today().isoformat()
        seeded = True

    current_health = initial_options.get(STATE_HEALTH)
    if current_health not in HEALTH_OPTIONS:
        initial_options[STATE_HEALTH] = DEFAULT_HEALTH
        seeded = True

    if seeded:
        hass.config_entries.async_update_entry(entry, options=initial_options)

    plant = PlantData(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = plant

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Startup moisture check ───────────────────────────────────────────────
    async def _startup_moisture_check() -> None:
        await plant.startup_moisture_check()

    hass.async_create_task(_startup_moisture_check())

    # ── Assign device to area if one was selected ────────────────────────────
    area_id: str | None = entry.data.get(CONF_AREA)
    if area_id:
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
        if device:
            dev_reg.async_update_device(device.id, area_id=area_id)

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
        _register_moisture_listener()
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
