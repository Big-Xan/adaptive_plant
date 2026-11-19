"""Repairs: old uploaded photos still public in www/adaptive_plant/.

1.2.4 and earlier saved uploads under www/, which Home Assistant serves without
signing in. Setup moves every photo a plant uses into private storage; files no
plant uses (e.g. from a setup wizard closed after uploading) are never deleted
automatically. This issue lists them and lets the user delete them, or keep
them and hide the notice (the issue is ignored, so it stays hidden).
"""
from __future__ import annotations

import posixpath

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_IMAGE_PATH, DOMAIN, is_owned_image_path, owned_image_filename
from .images import delete_public_uploads, unused_public_uploads

ISSUE_PUBLIC_PHOTOS = "public_photos"
_SHOW_AT_MOST = 10


def _referenced_uploads(hass: HomeAssistant) -> set[str]:
    """File names of the uploads plants use (same precedence as PlantData.image_path).

    A typed path that only reaches an upload through redundant segments
    (/local/adaptive_plant//<hex>.jpg, ./ or ../) is normalised first: the
    image entity still serves that file, so it must count as in use.
    """
    names: set[str] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if CONF_IMAGE_PATH in entry.options:
            path = entry.options[CONF_IMAGE_PATH]
        else:
            path = entry.data.get(CONF_IMAGE_PATH)
        if isinstance(path, str) and path and not is_owned_image_path(path):
            path = posixpath.normpath(path)
        if is_owned_image_path(path):
            names.add(owned_image_filename(path))
    return names


async def _async_unused(hass: HomeAssistant) -> list[str]:
    return await hass.async_add_executor_job(
        unused_public_uploads, hass.config.config_dir, _referenced_uploads(hass)
    )


def _placeholders(names: list[str]) -> dict[str, str]:
    shown = [f"- `{n}`" for n in names[:_SHOW_AT_MOST]]
    if len(names) > _SHOW_AT_MOST:
        shown.append(f"- … and {len(names) - _SHOW_AT_MOST} more")
    return {"count": str(len(names)), "files": "\n".join(shown)}


async def async_check_public_photos(hass: HomeAssistant) -> None:
    """Raise (or clear) the issue for unused uploads left in www/adaptive_plant/."""
    names = await _async_unused(hass)
    if not names:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_PUBLIC_PHOTOS)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_PUBLIC_PHOTOS,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_PUBLIC_PHOTOS,
        translation_placeholders=_placeholders(names),
    )


class PublicPhotosRepairFlow(RepairsFlow):
    """Delete the unused public uploads, or keep them and hide the notice."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> data_entry_flow.FlowResult:
        # Re-scan every time: a plant may have been added or removed since
        # the issue was raised, and a file it now uses must never be deleted.
        names = await _async_unused(self.hass)
        if not names:
            return self.async_create_entry(data={})
        if user_input is not None:
            if user_input.get("delete_photos"):
                await self.hass.async_add_executor_job(
                    delete_public_uploads, self.hass.config.config_dir, names
                )
                # Only report success once the files are really gone; if any
                # couldn't be deleted (read-only folder, permissions), abort so
                # the issue stays open and still lists them.
                left = set(await _async_unused(self.hass)) & set(names)
                if left:
                    return self.async_abort(
                        reason="delete_failed",
                        description_placeholders=_placeholders(sorted(left)),
                    )
                return self.async_create_entry(data={})
            # Keep: ignore the issue so it stays hidden across restarts.
            ir.async_ignore_issue(self.hass, DOMAIN, ISSUE_PUBLIC_PHOTOS, True)
            return self.async_abort(reason="kept")
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({vol.Required("delete_photos", default=False): bool}),
            description_placeholders=_placeholders(names),
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict | None
) -> RepairsFlow:
    return PublicPhotosRepairFlow()
