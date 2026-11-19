"""Image entity serving a plant's photo to signed-in users only.

Uploaded photos live in private storage (see images.py), which Home Assistant
does not serve. This entity is how they reach the dashboard: HA's image proxy
(/api/image_proxy/<entity_id>) answers authenticated requests, or requests
carrying the entity's current access token, which HA rotates every 5 minutes.
The Next watering sensor mirrors this entity's URL as its entity_picture so the
companion card and existing dashboards keep working unchanged.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, is_owned_image_path, photo_signal
from .images import private_image_file
from .plant import PlantData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    plant: PlantData = hass.data[DOMAIN][entry.entry_id]
    if plant.enable_image:
        async_add_entities([PlantPhotoImage(hass, plant, entry)])


class PlantPhotoImage(ImageEntity):
    """The plant's photo: an upload (private storage) or a path under /local/."""

    _attr_has_entity_name = True
    _attr_translation_key = "photo"

    def __init__(self, hass: HomeAssistant, plant: PlantData, entry: ConfigEntry) -> None:
        self._plant = plant
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_photo"
        self._shown: str | None = None
        super().__init__(hass)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._plant.plant_name,
            manufacturer="Adaptive Plant",
            model="Plant Monitor",
        )

    def _current_path(self) -> str | None:
        return self._plant.image_path if self._plant.enable_image else None

    @property
    def entity_picture(self) -> str | None:
        # No photo: no picture, rather than a proxy URL that can only fail.
        if not self._current_path():
            return None
        return super().entity_picture

    def _source_file(self) -> Path | None:
        """The file on disk behind the current path, or None."""
        path = self._current_path()
        if not path:
            return None
        if is_owned_image_path(path):
            return private_image_file(self.hass.config.config_dir, path)
        if path.startswith("/local/"):
            # A path the user typed: /local/ maps to <config>/www/. Never read
            # outside www/, whatever the path contains (.., symlinks).
            www = Path(self.hass.config.path("www")).resolve()
            target = (www / path[len("/local/"):]).resolve()
            if target == www or www not in target.parents:
                return None
            return target
        return None

    def image(self) -> bytes | None:
        """Blocking: read the photo (HA runs this in an executor)."""
        source = self._source_file()
        if source is None:
            return None
        try:
            data = source.read_bytes()
        except OSError:
            return None
        self._attr_content_type = mimetypes.guess_type(source.name)[0] or "image/jpeg"
        return data

    @callback
    def _publish(self) -> None:
        """Share the current URL with the Next watering sensor."""
        if self.hass is None or not self.entity_id:
            return  # still being constructed (ImageEntity.__init__ makes the first token)
        self._plant.photo_url = self.entity_picture
        async_dispatcher_send(self.hass, photo_signal(self._entry.entry_id))

    @callback
    def async_update_token(self) -> None:
        """HA rotates the token every 5 minutes; the old URL stops working soon after."""
        super().async_update_token()
        self._publish()

    async def async_added_to_hass(self) -> None:
        self._shown = self._current_path()
        if self._shown:
            self._attr_image_last_updated = dt_util.utcnow()
        self._plant.add_listener(self._on_plant_update)
        self._publish()

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)
        self._plant.photo_url = None
        async_dispatcher_send(self.hass, photo_signal(self._entry.entry_id))

    @callback
    def _on_plant_update(self) -> None:
        path = self._current_path()
        if path == self._shown:
            return
        # A new photo (or none): a new state tells viewers to fetch it again.
        self._shown = path
        self._attr_image_last_updated = dt_util.utcnow() if path else None
        self.async_write_ha_state()
        self._publish()
