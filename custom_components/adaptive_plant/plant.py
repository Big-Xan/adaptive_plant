"""Core PlantData model for the Adaptive Plant integration.

All business logic lives here. Entities subscribe to change notifications
and persist nothing themselves — all state is stored in config entry options.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Optional

from homeassistant.components.persistent_notification import async_create as pn_async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AREA,
    CONF_DRY_THRESHOLD,
    CONF_EARLY_WATERING_THRESHOLD,
    CONF_ENABLE_FERTILIZATION,
    CONF_ENABLE_IMAGE,
    CONF_ENABLE_NOTES,
    CONF_HEALTH_PROMPT_INTERVAL,
    CONF_IMAGE_PATH,
    CONF_LABEL,
    CONF_MOISTURE_SENSOR,
    CONF_PLANT_NAME,
    CONF_SNOOZE_THRESHOLD,
    CONF_WET_THRESHOLD,
    DEFAULT_EARLY_WATERING_THRESHOLD,
    DEFAULT_FERTILIZATION_INTERVAL,
    DEFAULT_HEALTH,
    DEFAULT_HEALTH_PROMPT_INTERVAL,
    DEFAULT_SNOOZE_THRESHOLD,
    DEFAULT_WATERING_INTERVAL,
    DOMAIN,
    HEALTH_OPTIONS,
    NOTIFICATION_ID_PREFIX,
    OPT_FERTILIZATION_INTERVAL,
    OPT_WATERING_INTERVAL,
    STATE_EARLY_WATERING_COUNT,
    STATE_HEALTH,
    STATE_HEALTH_LAST_UPDATED,
    STATE_LAST_FERTILIZED,
    STATE_LAST_WATERED,
    STATE_NEXT_FERTILIZED,
    STATE_NEXT_WATERING,
    STATE_NOTES,
    STATE_SNOOZE_COUNT,
    STATE_SNOOZED_THIS_PERIOD,
)

_LOGGER = logging.getLogger(__name__)


class PlantData:
    """Encapsulates all state and logic for a single plant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._listeners: list[Callable[[], None]] = []

    # ── Identity ────────────────────────────────────────────────────────────────

    @property
    def entry_id(self) -> str:
        return self._entry.entry_id

    @property
    def plant_name(self) -> str:
        return self._entry.data[CONF_PLANT_NAME]

    # ── Immutable config ─────────────────────────────────────────────────────────

    @property
    def early_watering_threshold(self) -> int:
        return int(
            self._entry.options.get(
                CONF_EARLY_WATERING_THRESHOLD,
                self._entry.data.get(CONF_EARLY_WATERING_THRESHOLD, DEFAULT_EARLY_WATERING_THRESHOLD),
            )
        )

    @property
    def snooze_threshold(self) -> int:
        return int(
            self._entry.options.get(
                CONF_SNOOZE_THRESHOLD,
                self._entry.data.get(CONF_SNOOZE_THRESHOLD, DEFAULT_SNOOZE_THRESHOLD),
            )
        )

    @property
    def health_prompt_interval(self) -> int:
        return int(
            self._entry.options.get(
                CONF_HEALTH_PROMPT_INTERVAL,
                self._entry.data.get(CONF_HEALTH_PROMPT_INTERVAL, DEFAULT_HEALTH_PROMPT_INTERVAL),
            )
        )

    @property
    def enable_fertilization(self) -> bool:
        return bool(self._entry.data.get(CONF_ENABLE_FERTILIZATION, False))

    @property
    def enable_notes(self) -> bool:
        return bool(self._entry.data.get(CONF_ENABLE_NOTES, False))

    @property
    def enable_image(self) -> bool:
        return bool(self._entry.data.get(CONF_ENABLE_IMAGE, False))

    @property
    def image_path(self) -> str | None:
        return self._entry.options.get(CONF_IMAGE_PATH) or self._entry.data.get(CONF_IMAGE_PATH)

    @property
    def area(self) -> str | None:
        return self._entry.data.get(CONF_AREA)

    @property
    def moisture_sensor(self) -> str | None:
        return self._entry.data.get(CONF_MOISTURE_SENSOR)

    @property
    def dry_threshold(self) -> float | None:
        val = self._entry.data.get(CONF_DRY_THRESHOLD)
        return float(val) if val is not None else None

    @property
    def wet_threshold(self) -> float | None:
        val = self._entry.data.get(CONF_WET_THRESHOLD)
        return float(val) if val is not None else None

    # ── Mutable config ───────────────────────────────────────────────────────────

    @property
    def watering_interval(self) -> int:
        return int(
            self._entry.options.get(
                OPT_WATERING_INTERVAL,
                self._entry.data.get(OPT_WATERING_INTERVAL, DEFAULT_WATERING_INTERVAL),
            )
        )

    @property
    def fertilization_interval(self) -> int:
        return int(
            self._entry.options.get(
                OPT_FERTILIZATION_INTERVAL,
                self._entry.data.get(OPT_FERTILIZATION_INTERVAL, DEFAULT_FERTILIZATION_INTERVAL),
            )
        )

    @property
    def label(self) -> str | None:
        """Optional display label for grouping plants within an area (e.g. 'Left shelf').
        Treats empty strings, whitespace-only, and the literal word 'null' as no label.
        """
        def _clean(val) -> str | None:
            if not val:
                return None
            stripped = val.strip()
            if not stripped or stripped.lower() == 'null':
                return None
            return stripped

        if CONF_LABEL in self._entry.options:
            return _clean(self._entry.options[CONF_LABEL])
        return _clean(self._entry.data.get(CONF_LABEL))

    # ── Runtime state ────────────────────────────────────────────────────────────

    @property
    def last_watered(self) -> str | None:
        return self._entry.options.get(STATE_LAST_WATERED)

    @property
    def next_watering(self) -> str | None:
        return self._entry.options.get(STATE_NEXT_WATERING)

    @property
    def early_watering_count(self) -> int:
        return int(self._entry.options.get(STATE_EARLY_WATERING_COUNT, 0))

    @property
    def snooze_count(self) -> int:
        return int(self._entry.options.get(STATE_SNOOZE_COUNT, 0))

    @property
    def snoozed_this_period(self) -> bool:
        return bool(self._entry.options.get(STATE_SNOOZED_THIS_PERIOD, False))

    @property
    def health(self) -> str:
        val = self._entry.options.get(STATE_HEALTH, DEFAULT_HEALTH)
        return val if val in HEALTH_OPTIONS else DEFAULT_HEALTH

    @property
    def health_last_updated(self) -> str | None:
        return self._entry.options.get(STATE_HEALTH_LAST_UPDATED)

    @property
    def last_fertilized(self) -> str | None:
        return self._entry.options.get(STATE_LAST_FERTILIZED)

    @property
    def next_fertilized(self) -> str | None:
        return self._entry.options.get(STATE_NEXT_FERTILIZED)

    @property
    def notes(self) -> str:
        return self._entry.options.get(STATE_NOTES, "")

    # ── Computed ─────────────────────────────────────────────────────────────────

    @property
    def days_until_watering(self) -> int | None:
        if not self.next_watering:
            return None
        try:
            delta = date.fromisoformat(self.next_watering) - date.today()
            return delta.days
        except ValueError:
            return None

    @property
    def days_until_fertilizing(self) -> int | None:
        if not self.next_fertilized:
            return None
        try:
            delta = date.fromisoformat(self.next_fertilized) - date.today()
            return delta.days
        except ValueError:
            return None

    @property
    def health_check_in_overdue(self) -> bool:
        """True if the health check-in interval has been exceeded."""
        health_updated_str = self.health_last_updated
        if not health_updated_str:
            return True
        try:
            days_since = (date.today() - date.fromisoformat(health_updated_str)).days
            return days_since >= self.health_prompt_interval
        except ValueError:
            return True

    # ── Listeners ────────────────────────────────────────────────────────────────

    def add_listener(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]) -> None:
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            cb()

    # ── Persistence ──────────────────────────────────────────────────────────────

    async def _persist(self, updates: dict) -> None:
        current = self._entry.options
        merged = {**current, **updates}
        if merged == current:
            return
        self._hass.config_entries.async_update_entry(self._entry, options=merged)
        self._notify_listeners()

    # ── Watering ─────────────────────────────────────────────────────────────────

    async def mark_watered(self) -> None:
        today = date.today()
        today_str = today.isoformat()
        interval = self.watering_interval
        early_count = self.early_watering_count

        # Adaptive interval reduction is skipped for moisture sensor plants —
        # the sensor drives watering decisions, schedule is a fallback only.
        if not self.moisture_sensor:
            next_watering_str = self.next_watering
            if next_watering_str:
                try:
                    scheduled = date.fromisoformat(next_watering_str)
                    if today < scheduled:
                        early_count += 1
                        if early_count >= self.early_watering_threshold:
                            interval = max(1, interval - 1)
                            early_count = 0
                            _LOGGER.debug(
                                "%s: early watering threshold reached — interval reduced to %d days",
                                self.plant_name, interval,
                            )
                    else:
                        early_count = 0
                except ValueError:
                    early_count = 0
            else:
                early_count = 0

        # Snooze streak tracking — skipped for moisture sensor plants.
        snooze_count = 0
        if not self.moisture_sensor:
            if self.snoozed_this_period:
                snooze_count = self.snooze_count + 1
            if snooze_count >= self.snooze_threshold:
                interval = min(365, interval + 1)
                snooze_count = 0
                _LOGGER.debug(
                    "%s: snooze threshold reached — interval increased to %d days",
                    self.plant_name, interval,
                )

        new_next = (today + timedelta(days=interval)).isoformat()
        await self._persist({
            STATE_LAST_WATERED: today_str,
            STATE_NEXT_WATERING: new_next,
            STATE_EARLY_WATERING_COUNT: early_count,
            STATE_SNOOZE_COUNT: snooze_count,
            STATE_SNOOZED_THIS_PERIOD: False,
            OPT_WATERING_INTERVAL: interval,
        })

    async def set_watering_interval(self, days: int) -> None:
        await self._persist({OPT_WATERING_INTERVAL: int(days)})

    async def snooze_watering(self) -> None:
        """Push next watering (and fertilization if also due today or overdue) forward by 1 day."""
        today = date.today()

        nw = self.next_watering
        if nw:
            try:
                new_next_watering = (date.fromisoformat(nw) + timedelta(days=1)).isoformat()
            except ValueError:
                new_next_watering = (today + timedelta(days=1)).isoformat()
        else:
            new_next_watering = (today + timedelta(days=1)).isoformat()

        updates = {STATE_NEXT_WATERING: new_next_watering}

        # Only track snooze streak for schedule-driven plants — moisture sensor
        # plants snooze silently without affecting the adaptive counter.
        if not self.moisture_sensor:
            updates[STATE_SNOOZED_THIS_PERIOD] = True

        # Also snooze fertilization if it is due today or overdue
        if self.enable_fertilization:
            nf = self.next_fertilized
            if nf:
                try:
                    nf_date = date.fromisoformat(nf)
                    if nf_date <= today:
                        updates[STATE_NEXT_FERTILIZED] = (nf_date + timedelta(days=1)).isoformat()
                        _LOGGER.debug(
                            "%s: fertilization also due — snoozing to %s",
                            self.plant_name, updates[STATE_NEXT_FERTILIZED],
                        )
                except ValueError:
                    pass

        await self._persist(updates)

    # ── Health ───────────────────────────────────────────────────────────────────

    async def set_health(self, value: str) -> None:
        if value not in HEALTH_OPTIONS:
            _LOGGER.warning("%s: invalid health value '%s' — ignored", self.plant_name, value)
            return
        # Always write timestamp even if value unchanged — resets the reminder
        # clock when user confirms current status without changing it.
        current = self._entry.options
        merged = {
            **current,
            STATE_HEALTH: value,
            STATE_HEALTH_LAST_UPDATED: date.today().isoformat(),
        }
        self._hass.config_entries.async_update_entry(self._entry, options=merged)
        self._notify_listeners()

    async def confirm_health(self) -> None:
        """Reset the health check-in clock without changing the health value."""
        current = self._entry.options
        merged = {
            **current,
            STATE_HEALTH_LAST_UPDATED: date.today().isoformat(),
        }
        self._hass.config_entries.async_update_entry(self._entry, options=merged)
        self._notify_listeners()

    # ── Fertilization ────────────────────────────────────────────────────────────

    async def mark_fertilized(self) -> None:
        today = date.today()
        new_next = (today + timedelta(days=self.fertilization_interval)).isoformat()
        await self._persist({
            STATE_LAST_FERTILIZED: today.isoformat(),
            STATE_NEXT_FERTILIZED: new_next,
        })

    async def set_fertilization_interval(self, days: int) -> None:
        await self._persist({OPT_FERTILIZATION_INTERVAL: int(days)})

    # ── Notes ────────────────────────────────────────────────────────────────────

    async def set_notes(self, value: str) -> None:
        await self._persist({STATE_NOTES: value})

    # ── Event-driven callbacks ───────────────────────────────────────────────────

    async def startup_moisture_check(self) -> None:
        """On HA startup, push next_watering forward if soil moisture is above
        the dry threshold and the plant is already due or overdue.

        Skips silently if:
        - No moisture sensor configured
        - No dry threshold configured
        - Sensor state is unknown/unavailable (Bluetooth/Zigbee not yet reported)
        - Plant is not yet due
        """
        if not self.moisture_sensor or self.dry_threshold is None:
            return

        nw = self.next_watering
        if not nw:
            return

        try:
            next_date = date.fromisoformat(nw)
        except ValueError:
            return

        today = date.today()
        if next_date > today:
            # Not yet due — nothing to fix
            return

        state = self._hass.states.get(self.moisture_sensor)
        if state is None or state.state in ("unknown", "unavailable"):
            _LOGGER.debug(
                "%s: startup moisture check skipped — sensor not yet available",
                self.plant_name,
            )
            return

        try:
            moisture = float(state.state)
        except (ValueError, TypeError):
            return

        if moisture > self.dry_threshold:
            new_next = (today + timedelta(days=1)).isoformat()
            _LOGGER.debug(
                "%s: startup moisture check — soil above dry threshold, pushing next watering to %s",
                self.plant_name,
                new_next,
            )
            await self._persist({STATE_NEXT_WATERING: new_next})

    async def daily_rollover(self) -> None:
        today = date.today()

        # For moisture sensor plants, check current soil moisture before
        # flagging as due. If moisture is above the dry threshold the plant
        # doesn't need watering yet — silently push the date by 1 day without
        # touching the snooze counter or adaptive logic.
        if self.moisture_sensor and self.dry_threshold is not None:
            state = self._hass.states.get(self.moisture_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    moisture = float(state.state)
                    if moisture > self.dry_threshold:
                        nw = self.next_watering
                        if nw:
                            try:
                                new_next = (date.fromisoformat(nw) + timedelta(days=1)).isoformat()
                            except ValueError:
                                new_next = (today + timedelta(days=1)).isoformat()
                        else:
                            new_next = (today + timedelta(days=1)).isoformat()
                        _LOGGER.debug(
                            "%s: moisture above dry threshold at rollover — pushing next watering to %s",
                            self.plant_name, new_next,
                        )
                        await self._persist({STATE_NEXT_WATERING: new_next})
                except (ValueError, TypeError):
                    pass

        health_updated_str = self.health_last_updated
        needs_notification = False

        if health_updated_str:
            try:
                days_since = (today - date.fromisoformat(health_updated_str)).days
                if days_since >= self.health_prompt_interval:
                    needs_notification = True
            except ValueError:
                needs_notification = True
        else:
            needs_notification = True

        if needs_notification:
            # Only fire once per day — compare last notified date to prevent
            # daily re-fire until the user presses Confirm Health.
            last_notified = self._entry.options.get("_health_notif_date")
            if last_notified != today.isoformat():
                days_since_val = None
                if health_updated_str:
                    try:
                        days_since_val = (today - date.fromisoformat(health_updated_str)).days
                    except ValueError:
                        pass
                self._fire_health_notification(days_since_val)
                await self._persist({"_health_notif_date": today.isoformat()})

        self._notify_listeners()

    def _fire_health_notification(self, days_since: int | None) -> None:
        body = (
            f"**{self.plant_name}** hasn't had a health check-in in "
            f"{days_since} day(s). Current status: **{self.health}**.\n\n"
            "Open the plant card and press **Confirm Health** when done.\n\n"
            "**Dismiss after updating plant health.**"
            if days_since is not None
            else f"**{self.plant_name}** has never had a health check-in recorded.\n\n"
            "Open the plant card and press **Confirm Health** when done.\n\n"
            "**Dismiss after updating plant health.**"
        )
        pn_async_create(
            self._hass,
            body,
            title=f"Plant Health Reminder: {self.plant_name}",
            notification_id=f"{NOTIFICATION_ID_PREFIX}{self.entry_id}",
        )

    async def handle_moisture_change(self, raw_state: str) -> None:
        try:
            moisture = float(raw_state)
        except (ValueError, TypeError):
            return

        dry = self.dry_threshold
        wet = self.wet_threshold
        today = date.today()

        if dry is not None and moisture < dry:
            nw = self.next_watering
            if nw:
                try:
                    if date.fromisoformat(nw) > today:
                        _LOGGER.debug(
                            "%s: moisture below dry threshold — rescheduling to today",
                            self.plant_name,
                        )
                        await self._persist({STATE_NEXT_WATERING: today.isoformat()})
                except ValueError:
                    pass
        elif wet is not None and moisture > wet:
            _LOGGER.debug(
                "%s: moisture above wet threshold — auto-marking watered",
                self.plant_name,
            )
            await self.mark_watered()
