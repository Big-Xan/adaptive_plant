"""Number entities for the Adaptive Plant integration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_FERTILIZATION_INTERVAL, DEFAULT_WATERING_INTERVAL, DOMAIN
from .plant import PlantData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    plant: PlantData = hass.data[DOMAIN][entry.entry_id]

    entities: list[PlantNumberBase] = [WateringIntervalNumber(plant, entry)]

    if plant.enable_fertilization:
        entities.append(FertilizationIntervalNumber(plant, entry))

    async_add_entities(entities)


class PlantNumberBase(NumberEntity):
    """Shared base for Adaptive Plant number entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "days"

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

    async def async_added_to_hass(self) -> None:
        self._plant.add_listener(self._on_plant_update)

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)

    @callback
    def _on_plant_update(self) -> None:
        self.async_write_ha_state()


class WateringIntervalNumber(PlantNumberBase):
    """Editable number for the watering interval in days."""

    _attr_translation_key = "watering_interval_days"
    _attr_icon = "mdi:calendar-clock"
    _attr_native_min_value = 1
    _attr_native_max_value = 365
    _attr_native_step = 1

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_watering_interval"

    @property
    def native_value(self) -> float:
        return float(self._plant.watering_interval)

    async def async_set_native_value(self, value: float) -> None:
        await self._plant.set_watering_interval(int(value))


class FertilizationIntervalNumber(PlantNumberBase):
    """Editable number for the fertilization interval in days."""

    _attr_translation_key = "fertilization_interval_days"
    _attr_icon = "mdi:bottle-tonic-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = 365
    _attr_native_step = 1

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_fertilization_interval"

    @property
    def native_value(self) -> float:
        return float(self._plant.fertilization_interval)

    async def async_set_native_value(self, value: float) -> None:
        await self._plant.set_fertilization_interval(int(value))