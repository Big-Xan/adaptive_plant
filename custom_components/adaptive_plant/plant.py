"""Core PlantData model for the Adaptive Plant integration.

All business logic lives here. Entities subscribe to change notifications
and persist nothing themselves — all state is stored in config entry options.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta

from homeassistant.components.persistent_notification import async_create as pn_async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
    CONF_LABEL,
    CONF_LATIN_NAME,
    CONF_MOISTURE_SENSOR,
    CONF_NOTES_ENABLED,
    CONF_PLANT_NAME,
    CONF_REPOTTING_ENABLED,
    CONF_SNOOZE_THRESHOLD,
    CONF_WET_THRESHOLD,
    DEFAULT_EARLY_WATERING_THRESHOLD,
    DEFAULT_FERT_SYNC_WINDOW,
    DEFAULT_FERTILIZATION_INTERVAL,
    DEFAULT_HEALTH,
    DEFAULT_HEALTH_PROMPT_INTERVAL,
    DEFAULT_SNOOZE_THRESHOLD,
    DEFAULT_WATERING_INTERVAL,
    HEALTH_OPTIONS,
    NOTIFICATION_ID_PREFIX,
    OPT_FERTILIZATION_INTERVAL,
    OPT_FERT_SYNC_WINDOW,
    OPT_WATERING_INTERVAL,
    STATE_EARLY_WATERING_COUNT,
    STATE_HEALTH,
    STATE_HEALTH_LAST_UPDATED,
    STATE_HEALTH_NOTIF_DATE,
    STATE_LAST_FERTILIZED,
    STATE_LAST_REPOTTED,
    STATE_REPOTTED_DATE_INPUT,
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
        # Options override takes precedence — allows toggling after setup
        # (including enabling it on plants where it was skipped at setup).
        if CONF_FERTILIZATION_ENABLED in self._entry.options:
            return bool(self._entry.options[CONF_FERTILIZATION_ENABLED])
        return bool(self._entry.data.get(CONF_ENABLE_FERTILIZATION, False))

    @property
    def enable_notes(self) -> bool:
        # Options override takes precedence — allows toggling after setup.
        # Falls back to the original entry.data value set during setup.
        if CONF_NOTES_ENABLED in self._entry.options:
            return bool(self._entry.options[CONF_NOTES_ENABLED])
        return bool(self._entry.data.get(CONF_ENABLE_NOTES, False))

    @property
    def enable_latin_name(self) -> bool:
        # Options override takes precedence — allows enabling after setup.
        if CONF_ENABLE_LATIN_NAME in self._entry.options:
            return bool(self._entry.options[CONF_ENABLE_LATIN_NAME])
        return bool(self._entry.data.get(CONF_ENABLE_LATIN_NAME, False))

    @property
    def enable_repotting(self) -> bool:
        # Options override takes precedence — allows toggling after setup.
        if CONF_REPOTTING_ENABLED in self._entry.options:
            return bool(self._entry.options[CONF_REPOTTING_ENABLED])
        return bool(self._entry.data.get(CONF_ENABLE_REPOTTING, False))

    @property
    def latin_name(self) -> str | None:
        # Check options first using key presence — an empty string in options
        # means the user intentionally cleared it, so don't fall back to entry.data.
        if CONF_LATIN_NAME in self._entry.options:
            val = self._entry.options[CONF_LATIN_NAME]
            return val.strip() if val and val.strip() else None
        val = self._entry.data.get(CONF_LATIN_NAME)
        return val.strip() if val and val.strip() else None

    @property
    def enable_image(self) -> bool:
        # Options override takes precedence — allows enabling after setup.
        if CONF_ENABLE_IMAGE in self._entry.options:
            return bool(self._entry.options[CONF_ENABLE_IMAGE])
        return bool(self._entry.data.get(CONF_ENABLE_IMAGE, False))

    @property
    def image_path(self) -> str | None:
        # Check options first using key presence — an empty string in options
        # means the user intentionally cleared it, so don't fall back to entry.data.
        if CONF_IMAGE_PATH in self._entry.options:
            val = self._entry.options[CONF_IMAGE_PATH]
            return val if val else None
        return self._entry.data.get(CONF_IMAGE_PATH)

    @property
    def area(self) -> str | None:
        return self._entry.data.get(CONF_AREA)

    @property
    def moisture_sensor(self) -> str | None:
        # Key-presence check (same pattern as image_path): the options flow
        # writes an empty-string tombstone when the moisture toggle is
        # switched off. The tombstone must shadow the entry.data fallback,
        # otherwise a sensor selected during the original setup wizard
        # resurrects after being disabled.
        if CONF_MOISTURE_SENSOR in self._entry.options:
            val = self._entry.options[CONF_MOISTURE_SENSOR]
            return val if val else None
        return self._entry.data.get(CONF_MOISTURE_SENSOR)

    @property
    def dry_threshold(self) -> float | None:
        val = self._entry.options.get(CONF_DRY_THRESHOLD) if CONF_DRY_THRESHOLD in self._entry.options else self._entry.data.get(CONF_DRY_THRESHOLD)
        return float(val) if val is not None else None

    @property
    def wet_threshold(self) -> float | None:
        val = self._entry.options.get(CONF_WET_THRESHOLD) if CONF_WET_THRESHOLD in self._entry.options else self._entry.data.get(CONF_WET_THRESHOLD)
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
    def fertilization_sync_window(self) -> int:
        """Days within which marking watered snaps fertilization onto the watering day.

        0 disables the feature. Options-first with an entry.data fallback,
        mirroring the interval properties.
        """
        return int(
            self._entry.options.get(
                OPT_FERT_SYNC_WINDOW,
                self._entry.data.get(OPT_FERT_SYNC_WINDOW, DEFAULT_FERT_SYNC_WINDOW),
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

    @property
    def last_repotted(self) -> str | None:
        return self._entry.options.get(STATE_LAST_REPOTTED)

    @property
    def repotted_date_input(self) -> str:
        """The user-editable date correction field. Empty string when not set."""
        return self._entry.options.get(STATE_REPOTTED_DATE_INPUT, "")

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

        updates = {
            STATE_LAST_WATERED: today_str,
            STATE_NEXT_WATERING: new_next,
            STATE_EARLY_WATERING_COUNT: early_count,
            STATE_SNOOZE_COUNT: snooze_count,
            STATE_SNOOZED_THIS_PERIOD: False,
            OPT_WATERING_INTERVAL: interval,
        }

        # ── Fertilization sync ──────────────────────────────────────────────
        # If the freshly-scheduled watering day falls within the configured
        # window of an upcoming fertilization date, snap fertilization onto the
        # watering day so both tasks land together ("fertilizer in the watering
        # can"). Compares the two real dates at water time, so it tracks adaptive
        # interval changes and snoozes naturally. Excluded for moisture-sensor
        # plants (no dependable schedule), and only ever moves a *future*
        # fertilization — never delays one already due, and avoids chasing.
        window = self.fertilization_sync_window
        if self.enable_fertilization and not self.moisture_sensor and window > 0:
            nf = self.next_fertilized
            if nf:
                try:
                    nf_date = date.fromisoformat(nf)
                    water_date = today + timedelta(days=interval)
                    if nf_date > today and abs((water_date - nf_date).days) <= window:
                        updates[STATE_NEXT_FERTILIZED] = new_next
                        _LOGGER.debug(
                            "%s: fertilization within %d day(s) of watering — snapping to %s",
                            self.plant_name, window, new_next,
                        )
                except ValueError:
                    pass

        await self._persist(updates)

    async def set_watering_interval(self, days: int) -> None:
        await self._persist({OPT_WATERING_INTERVAL: int(days)})

    async def snooze_watering(self) -> None:
        """Push next watering and/or fertilization forward by 1 day if due or overdue.

        Watering is only snoozed if it is actually due or overdue today — pressing
        Snooze when only fertilization is due must not touch the watering date or
        the adaptive snooze streak counter.
        """
        today = date.today()
        updates: dict = {}

        # Snooze watering only if it is due or overdue
        nw = self.next_watering
        watering_due = False
        if nw:
            try:
                nw_date = date.fromisoformat(nw)
                if nw_date <= today:
                    watering_due = True
                    updates[STATE_NEXT_WATERING] = (nw_date + timedelta(days=1)).isoformat()
                    _LOGGER.debug(
                        "%s: watering due — snoozing to %s",
                        self.plant_name, updates[STATE_NEXT_WATERING],
                    )
            except ValueError:
                pass

        # Only track snooze streak when watering was actually due and the plant
        # is schedule-driven — moisture sensor plants snooze silently.
        if watering_due and not self.moisture_sensor:
            updates[STATE_SNOOZED_THIS_PERIOD] = True

        # Snooze fertilization if it is due today or overdue
        if self.enable_fertilization:
            nf = self.next_fertilized
            if nf:
                try:
                    nf_date = date.fromisoformat(nf)
                    if nf_date <= today:
                        updates[STATE_NEXT_FERTILIZED] = (nf_date + timedelta(days=1)).isoformat()
                        _LOGGER.debug(
                            "%s: fertilization due — snoozing to %s",
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
        # No-op when the value would not change. Resetting the check-in clock
        # without changing the health value is the job of confirm_health().
        if value == self.health:
            return
        await self._persist({
            STATE_HEALTH: value,
            STATE_HEALTH_LAST_UPDATED: date.today().isoformat(),
        })

    async def confirm_health(self) -> None:
        """Reset the health check-in clock without changing the health value."""
        await self._persist({
            STATE_HEALTH_LAST_UPDATED: date.today().isoformat(),
        })

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

    async def set_latin_name(self, value: str) -> None:
        await self._persist({CONF_LATIN_NAME: value.strip() or ""})

    # ── Repotting ─────────────────────────────────────────────────────────────

    async def mark_repotted(self) -> None:
        """Stamp the repotting date.

        Uses the value of the repotted_date_input text entity if it contains a
        valid ISO date, otherwise falls back to today. Clears the input field
        after stamping so it doesn't linger as a stale suggestion.
        """
        today = date.today()
        raw = self.repotted_date_input.strip()
        stamp: str
        if raw:
            try:
                date.fromisoformat(raw)   # validate
                stamp = raw
            except ValueError:
                _LOGGER.warning(
                    "%s: repotted_date_input '%s' is not a valid ISO date — using today",
                    self.plant_name, raw,
                )
                stamp = today.isoformat()
        else:
            stamp = today.isoformat()

        await self._persist({
            STATE_LAST_REPOTTED: stamp,
            STATE_REPOTTED_DATE_INPUT: "",   # clear the correction field
        })

    async def set_repotted_date_input(self, value: str) -> None:
        """Store a prospective repotting date typed by the user."""
        await self._persist({STATE_REPOTTED_DATE_INPUT: value.strip()})

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
        # Track whether anything was actually persisted this rollover. _persist
        # notifies listeners on real change; we only need a trailing notify
        # when nothing changed but the date rolled over, so date-derived
        # display sensors (Days Until Watering, etc.) still refresh.
        persisted = False

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
                        persisted = True
                except (ValueError, TypeError):
                    pass

        # Health check-in reminder — compute days_since once. A missing or
        # malformed timestamp is treated as "never updated" (needs notification).
        health_updated_str = self.health_last_updated
        days_since: int | None = None
        if health_updated_str:
            try:
                days_since = (today - date.fromisoformat(health_updated_str)).days
            except ValueError:
                pass

        needs_notification = (
            days_since is None or days_since >= self.health_prompt_interval
        )

        if needs_notification:
            # Only fire once per day — prevent daily re-fire until user presses
            # Confirm Health (which resets STATE_HEALTH_LAST_UPDATED).
            last_notified = self._entry.options.get(STATE_HEALTH_NOTIF_DATE)
            if last_notified != today.isoformat():
                self._fire_health_notification(days_since)
                await self._persist({STATE_HEALTH_NOTIF_DATE: today.isoformat()})
                persisted = True

        # If nothing was persisted, fire listeners explicitly so date-derived
        # display values refresh for the new day. When _persist fires it has
        # already notified, so we skip the trailing call to avoid double-fire.
        if not persisted:
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
        elif dry is not None and moisture > dry:
            # Self-healing for missed rollover checks. The 00:05 rollover
            # only pushes next_watering forward if the sensor is available
            # at that exact moment; battery/BLE sensors are often asleep or
            # unavailable overnight. If the check is missed, the plant gets
            # stuck showing due — mid-band readings (dry < m < wet)
            # previously fell through both branches above and never
            # corrected it. Apply the same correction the rollover would
            # have: soil is moist and the plant is flagged due, so push to
            # tomorrow without touching snooze or adaptive logic. No-ops
            # once next_watering is in the future, so this fires at most
            # once per day. (GitHub issue #11)
            nw = self.next_watering
            if nw:
                try:
                    if date.fromisoformat(nw) <= today:
                        new_next = (today + timedelta(days=1)).isoformat()
                        _LOGGER.debug(
                            "%s: due but moisture above dry threshold — pushing next watering to %s",
                            self.plant_name,
                            new_next,
                        )
                        await self._persist({STATE_NEXT_WATERING: new_next})
                except ValueError:
                    pass
