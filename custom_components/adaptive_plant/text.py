"""Text entity for free-form plant notes and latin name."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_LATIN_NAME, DOMAIN, STATE_NOTES
from .plant import PlantData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    plant: PlantData = hass.data[DOMAIN][entry.entry_id]
    entities = []
    if plant.enable_notes:
        entities.append(NotesText(plant, entry))
    if plant.enable_latin_name:
        entities.append(LatinNameText(plant, entry))
    if entities:
        async_add_entities(entities)


class NotesText(TextEntity):
    """Text entity for storing free-form notes about a plant."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "notes"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_icon = "mdi:note-text"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        self._plant = plant
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_notes"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._plant.plant_name,
            manufacturer="Adaptive Plant",
            model="Plant Monitor",
        )

    @property
    def available(self) -> bool:
        return self._plant.enable_notes

    @property
    def native_value(self) -> str:
        return self._plant.notes

    async def async_added_to_hass(self) -> None:
        self._plant.add_listener(self._on_plant_update)

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)

    @callback
    def _on_plant_update(self) -> None:
        self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        await self._plant.set_notes(value)


class LatinNameText(TextEntity):
    """Text entity for storing and editing the plant's latin name."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "latin_name"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_icon = "mdi:flower-outline"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        self._plant = plant
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_latin_name"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._plant.plant_name,
            manufacturer="Adaptive Plant",
            model="Plant Monitor",
        )

    @property
    def available(self) -> bool:
        return self._plant.enable_latin_name

    @property
    def native_value(self) -> str:
        return self._plant.latin_name or ""

    async def async_added_to_hass(self) -> None:
        self._plant.add_listener(self._on_plant_update)

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)

    @callback
    def _on_plant_update(self) -> None:
        self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        await self._plant.set_latin_name(value)
