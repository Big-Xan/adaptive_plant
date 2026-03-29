"""Adaptive Plant integration — entry point."""
from __future__ import annotations

import logging
from datetime import date

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
    STATE_LAST_WATERED,
    STATE_NEXT_FERTILIZED,
    STATE_NEXT_WATERING,
)
from .plant import PlantData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Adaptive Plant config entry."""
    hass.data.setdefault(DOMAIN, {})

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

    # Seed watering interval from data into options if not already there
    if OPT_WATERING_INTERVAL not in initial_options and OPT_WATERING_INTERVAL in entry.data:
        initial_options[OPT_WATERING_INTERVAL] = entry.data[OPT_WATERING_INTERVAL]
        seeded = True

    # Seed health_last_updated on first load so fresh plants don't immediately
    # trigger a health reminder notification on their first daily rollover.
    if STATE_HEALTH_LAST_UPDATED not in initial_options:
        initial_options[STATE_HEALTH_LAST_UPDATED] = date.today().isoformat()
        seeded = True

    # Seed STATE_HEALTH so the HealthSelect entity always reads a real health
    # string from options. Also corrects any existing entry where a non-health
    # value (e.g. a timestamp) was previously stored under this key.
    current_health = initial_options.get(STATE_HEALTH)
    if current_health not in HEALTH_OPTIONS:
        initial_options[STATE_HEALTH] = DEFAULT_HEALTH
        seeded = True

    if seeded:
        hass.config_entries.async_update_entry(entry, options=initial_options)

    plant = PlantData(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = plant

    # Forward to all entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Startup moisture check ───────────────────────────────────────────────
    # Deferred as a task so it doesn't block entry setup. For moisture sensor
    # plants that were already overdue before 1.0.4 was installed, pushes
    # next_watering forward by 1 day if soil is above the dry threshold.
    # Skips gracefully if the sensor hasn't reported yet — nightly rollover
    # at 00:05 will catch it.
    async def _startup_moisture_check() -> None:
        await plant.startup_moisture_check()

    hass.async_create_task(_startup_moisture_check())

    # ── Assign device to area if one was selected ────────────────────────────
    area_id: str | None = entry.data.get(CONF_AREA)
    if area_id:
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_device(
            identifiers={(DOMAIN, entry.entry_id)}
        )
        if device:
            dev_reg.async_update_device(device.id, area_id=area_id)

    # ── Daily rollover at 00:05 ──────────────────────────────────────────────
    async def _daily_rollover(now):
        await plant.daily_rollover()

    entry.async_on_unload(
        async_track_time_change(hass, _daily_rollover, hour=0, minute=5, second=0)
    )

    # ── Moisture sensor listener ─────────────────────────────────────────────
    # Wrapped in a helper so it can be re-called when options change (e.g. the
    # user adds, changes, or removes a moisture sensor via the options flow).
    _moisture_unsub = None

    def _register_moisture_listener() -> None:
        nonlocal _moisture_unsub
        # Tear down the previous listener if one exists
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
    # Re-registers the moisture listener whenever the user saves new options,
    # so adding/changing/removing a sensor takes effect without a full restart.
    async def _handle_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
        _register_moisture_listener()
        plant._notify_listeners()

    entry.async_on_unload(entry.add_update_listener(_handle_options_update))

    # Ensure the moisture unsub is cleaned up on unload
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
