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
    DOMAIN,
    OPT_WATERING_INTERVAL,
    PLATFORMS,
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

    if seeded:
        hass.config_entries.async_update_entry(entry, options=initial_options)

    plant = PlantData(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = plant

    # Forward to all entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
    moisture_sensor: str | None = entry.data.get(CONF_MOISTURE_SENSOR)
    if moisture_sensor:

        async def _moisture_state_changed(event: Event) -> None:
            new_state = event.data.get("new_state")
            if new_state is not None and new_state.state not in ("unknown", "unavailable"):
                await plant.handle_moisture_change(new_state.state)

        entry.async_on_unload(
            async_track_state_change_event(
                hass, [moisture_sensor], _moisture_state_changed
            )
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Adaptive Plant config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
