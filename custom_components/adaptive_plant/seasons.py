"""Seasonal schedules (Experimental) — pure date logic.

No Home Assistant imports, and no calls to date.today(): every function takes
`today` explicitly, so the logic can be tested against any date without
touching a clock. PlantData (plant.py) and the flows are the only callers.

Model
-----
* The **base schedule** (options key CONF_SEASON_BASE) is the plant's normal
  schedule: {"interval": int, "fert_interval": int}. It is in effect on every
  day no season covers.
* Each **season** (list under CONF_SEASONS) covers a date range, start and end
  inclusive, and may run across New Year:
      {"name": str, "start": "MM-DD", "end": "MM-DD", "interval": int,
       "fert_interval": int (optional), "pause_fertilization": bool}
  Seasons never overlap (the flows enforce it). A season without
  "fert_interval" uses the base's.
* The base and each season learn their own watering interval: whichever
  **period** is in effect takes every interval change (see write_back).

Days are compared as (month, day) tuples, so Feb 29 needs no special case: a
season starting 02-29 starts on Mar 1 in non-leap years, and one ending 02-29
ends on Feb 28.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from .const import (
    SEASON_END,
    SEASON_FERT_INTERVAL,
    SEASON_INTERVAL,
    SEASON_PAUSE_FERT,
    SEASON_START,
)

BASE_ID = "base"

# Every (month, day) of a leap year: the calendar used for overlap checks.
_ALL_DAYS = [
    ((date(2000, 1, 1) + timedelta(days=i)).month, (date(2000, 1, 1) + timedelta(days=i)).day)
    for i in range(366)
]


def parse_md(value) -> tuple[int, int]:
    """Parse "MM-DD" into (month, day); raise ValueError if invalid.

    Validated against a leap year so 02-29 is accepted.
    """
    month_s, day_s = str(value).split("-")
    month, day = int(month_s), int(day_s)
    date(2000, month, day)
    return month, day


def format_md(month: int, day: int) -> str:
    """Build the stored "MM-DD" string; raise ValueError if the day is invalid."""
    date(2000, int(month), int(day))
    return f"{int(month):02d}-{int(day):02d}"


def _bounds(season) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """(start, end) of a well-formed season, or None. Never raises."""
    if not isinstance(season, dict):
        return None
    try:
        start = parse_md(season.get(SEASON_START))
        end = parse_md(season.get(SEASON_END))
        if int(season.get(SEASON_INTERVAL)) < 1:
            return None
    except (TypeError, ValueError, AttributeError):
        return None
    return start, end


def _contains(bounds, md: tuple[int, int]) -> bool:
    start, end = bounds
    if start <= end:
        return start <= md <= end
    return md >= start or md <= end          # runs across New Year


def valid_seasons(table) -> list[dict]:
    """The well-formed seasons in `table`, in calendar order of their start.

    Malformed entries (including v1 seasons without an end date) are skipped
    rather than raised: the flows validate on save, and runtime must never
    crash on a hand-edited entry. Returns the dicts from `table` itself.
    """
    if not isinstance(table, list):
        return []
    out = [s for s in table if _bounds(s) is not None]
    out.sort(key=lambda s: str(s.get(SEASON_START)))
    return out


def season_days(season) -> set[tuple[int, int]]:
    """Every (month, day) the season covers, on a leap-year calendar."""
    bounds = _bounds(season)
    if bounds is None:
        return set()
    return {md for md in _ALL_DAYS if _contains(bounds, md)}


def overlaps(season, others) -> bool:
    """True if `season` shares any day with one of `others`."""
    days = season_days(season)
    return any(days & season_days(o) for o in others)


def active_season(table, day: date) -> dict | None:
    """The season covering `day`, or None when the base schedule is in effect."""
    md = (day.month, day.day)
    for season in valid_seasons(table):
        if _contains(_bounds(season), md):
            return season
    return None


def period_id(season: dict | None) -> str:
    """Stable id of a period: a season's start date, or BASE_ID."""
    return str(season.get(SEASON_START)) if season else BASE_ID


def period_water(season: dict | None, base: dict) -> int:
    """Watering interval of a period (a season, or None for the base)."""
    src = season if season else base
    return int(src.get(SEASON_INTERVAL))


def period_fert(season: dict | None, base: dict) -> int | None:
    """Fertilization interval of a period: the season's own, else the base's."""
    if season and season.get(SEASON_FERT_INTERVAL) is not None:
        return int(season[SEASON_FERT_INTERVAL])
    val = base.get(SEASON_FERT_INTERVAL)
    return int(val) if val is not None else None


def valid_base(base) -> bool:
    if not isinstance(base, dict):
        return False
    try:
        return int(base.get(SEASON_INTERVAL)) >= 1
    except (TypeError, ValueError):
        return False


def is_fert_paused(table, day: date) -> bool:
    """True if the season covering `day` pauses fertilization (the base never does)."""
    season = active_season(table, day)
    return bool(season and season.get(SEASON_PAUSE_FERT))


def pauses_whole_year(table) -> bool:
    """True if paused seasons together cover every day, so fertilization never resumes."""
    paused: set = set()
    for season in valid_seasons(table):
        if season.get(SEASON_PAUSE_FERT):
            paused |= season_days(season)
    return len(paused) == len(_ALL_DAYS)


def clamp_fert_date(candidate: date, table, today: date) -> date:
    """Move a fertilization date out of any paused period.

    A date inside a pause moves to the first day after it that isn't paused.
    If today itself is paused, a past (overdue) date is first lifted to today,
    so fertilization is never shown due during a pause and comes due on the
    first unpaused day. Other dates are returned unchanged. Walks day by day so
    active_season stays the single source of truth for every calendar edge. If
    every day is paused (the flows forbid it) the candidate is returned as is.
    """
    if not valid_seasons(table):
        return candidate
    day = candidate
    if day < today and is_fert_paused(table, today):
        day = today
    for _ in range(367):
        if not is_fert_paused(table, day):
            return day
        day += timedelta(days=1)
    return candidate


def flip_next(last_event: str | None, interval: int, today: date) -> str | None:
    """Next due date after a change of interval: max(last event + interval, today).

    Keeps the last watered / fertilized date and fits it to the new interval.
    The today floor stops a shorter interval from making the plant look
    several days overdue on the day of the change. None without a usable date.
    """
    if not last_event:
        return None
    try:
        last = date.fromisoformat(last_event)
    except ValueError:
        return None
    return max(last + timedelta(days=int(interval)), today).isoformat()


def write_back(table, base, today: date, water: int | None = None,
               fert: int | None = None) -> tuple[list, dict]:
    """Copies of (table, base) with an interval written to the period in effect.

    Every door that changes the plant's interval (adaptive learning, the
    number entities, Plant settings) goes through here, so each period learns
    its own value. Never mutates its inputs: they are live entry.options
    values, and mutating them in place would make PlantData._persist see no
    change and skip the write.
    """
    new_table = copy.deepcopy(table) if isinstance(table, list) else []
    new_base = copy.deepcopy(base) if isinstance(base, dict) else {}
    target = active_season(new_table, today) or new_base
    if water is not None:
        target[SEASON_INTERVAL] = int(water)
    if fert is not None:
        target[SEASON_FERT_INTERVAL] = int(fert)
    return new_table, new_base


def rebase_fert(last_fertilized: str | None, interval: int, table, today: date) -> str | None:
    """Fresh next-fertilization date: max(last fertilized + interval, today), out of any pause.

    Used when the paused days change or seasons are turned off, where an
    existing pause-resume date may no longer apply.
    """
    nxt = flip_next(last_fertilized, interval, today)
    if nxt is None:
        return None
    return clamp_fert_date(date.fromisoformat(nxt), table, today).isoformat()
