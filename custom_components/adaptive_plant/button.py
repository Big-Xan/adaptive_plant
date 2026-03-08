"""Button entities for the Adaptive Plant integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .plant import PlantData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    plant: PlantData = hass.data[DOMAIN][entry.entry_id]

    entities: list[PlantButtonBase] = [
        MarkWateredButton(plant, entry),
        SnoozeWateringButton(plant, entry),
    ]

    if plant.enable_fertilization:
        entities.append(MarkFertilizedButton(plant, entry))

    async_add_entities(entities)


class PlantButtonBase(ButtonEntity):
    """Shared base for Adaptive Plant button entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        self._plant = plant
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._plant.plant_name,
            manufacturer="Adaptive Plant",
            model="Plant Monitor",
        )


class MarkWateredButton(PlantButtonBase):
    """Button that records a watering event and triggers adaptive logic."""

    _attr_translation_key = "mark_watered"
    _attr_icon = "mdi:watering-can"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_mark_watered"

    async def async_press(self) -> None:
        await self._plant.mark_watered()


class SnoozeWateringButton(PlantButtonBase):
    """Button that delays watering by one day and tracks snooze streaks."""

    _attr_translation_key = "snooze_watering"
    _attr_icon = "mdi:alarm-snooze"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_snooze_watering"

    async def async_press(self) -> None:
        await self._plant.snooze_watering()


class MarkFertilizedButton(PlantButtonBase):
    """Button that records a fertilization event."""

    _attr_translation_key = "mark_fertilized"
    _attr_icon = "mdi:bottle-tonic"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_mark_fertilized"

    async def async_press(self) -> None:
        await self._plant.mark_fertilized()