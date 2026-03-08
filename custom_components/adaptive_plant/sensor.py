"""Sensor entities for the Adaptive Plant integration."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    entities: list[PlantSensorBase] = [
        LastWateredSensor(plant, entry),
        NextWateringSensor(plant, entry),
        DaysUntilWateringSensor(plant, entry),
    ]

    if plant.enable_fertilization:
        entities += [
            LastFertilizedSensor(plant, entry),
            NextFertilizedSensor(plant, entry),
            DaysUntilFertilizingSensor(plant, entry),
        ]

    async_add_entities(entities)


class PlantSensorBase(SensorEntity):
    """Shared base for all Adaptive Plant sensor entities."""

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
            entry_type=None,
        )

    async def async_added_to_hass(self) -> None:
        self._plant.add_listener(self._on_plant_update)

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)

    @callback
    def _on_plant_update(self) -> None:
        self.async_write_ha_state()


class LastWateredSensor(PlantSensorBase):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "last_watered"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_watered"

    @property
    def native_value(self) -> date | None:
        val = self._plant.last_watered
        if val:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return None


class NextWateringSensor(PlantSensorBase):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_watering"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_watering"

    @property
    def native_value(self) -> date | None:
        val = self._plant.next_watering
        if val:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return None

    @property
    def entity_picture(self) -> str | None:
        if self._plant.enable_image:
            return self._plant.image_path
        return None


class DaysUntilWateringSensor(PlantSensorBase):
    _attr_translation_key = "days_until_watering"
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_days_until_watering"

    @property
    def native_value(self) -> str | None:
        days = self._plant.days_until_watering
        if days is None:
            return None
        if days == 0:
            return "Today"
        if days == -1:
            return "1 Day Overdue"
        if days < 0:
            return f"{abs(days)} Days Overdue"
        if days == 1:
            return "In 1 Day"
        return f"In {days} Days"


class LastFertilizedSensor(PlantSensorBase):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "last_fertilized"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_fertilized"

    @property
    def native_value(self) -> date | None:
        val = self._plant.last_fertilized
        if val:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return None


class NextFertilizedSensor(PlantSensorBase):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_fertilized"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_fertilized"

    @property
    def native_value(self) -> date | None:
        val = self._plant.next_fertilized
        if val:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return None


class DaysUntilFertilizingSensor(PlantSensorBase):
    _attr_translation_key = "days_until_fertilizing"
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_days_until_fertilizing"

    @property
    def native_value(self) -> str | None:
        days = self._plant.days_until_fertilizing
        if days is None:
            return None
        if days == 0:
            return "Today"
        if days == -1:
            return "1 Day Overdue"
        if days < 0:
            return f"{abs(days)} Days Overdue"
        if days == 1:
            return "In 1 Day"
        return f"In {days} Days"