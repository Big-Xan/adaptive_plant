"""Sensor entities for the Adaptive Plant integration."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
        EarlyWateringCountSensor(plant, entry),
        SnoozeCountSensor(plant, entry),
        CurrentMoistureSensor(plant, entry),
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

    @property
    def extra_state_attributes(self) -> dict:
        """Expose label as an attribute so the companion card can read it."""
        attrs = {}
        if self._plant.label:
            attrs["label"] = self._plant.label
        return attrs


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


class EarlyWateringCountSensor(PlantSensorBase):
    """Diagnostic sensor showing how many times the plant has been watered early in the current period."""

    _attr_translation_key = "early_watering_count"
    _attr_icon = "mdi:water-plus"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "times"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_early_watering_count"

    @property
    def native_value(self) -> int:
        return self._plant.early_watering_count


class SnoozeCountSensor(PlantSensorBase):
    """Diagnostic sensor showing how many consecutive periods watering has been snoozed."""

    _attr_translation_key = "snooze_count"
    _attr_icon = "mdi:alarm-snooze"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "times"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_snooze_count"

    @property
    def native_value(self) -> int:
        return self._plant.snooze_count


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


class CurrentMoistureSensor(PlantSensorBase):
    """Diagnostic sensor that mirrors the linked moisture sensor's current reading.

    Always created so it appears on the device page in the HA integration panel.
    Disabled by default when no moisture sensor is configured; automatically
    enabled once a sensor is assigned (requires entry reload after options save).
    """

    _attr_translation_key = "current_moisture"
    _attr_icon = "mdi:water-percent"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        super().__init__(plant, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_moisture"
        # Always enabled — availability is controlled dynamically via the
        # `available` property below. When no sensor is configured the entity
        # shows as unavailable rather than requiring manual enable/disable.
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self) -> float | None:
        sensor_id = self._plant.moisture_sensor
        if not sensor_id:
            return None
        state = self._plant._hass.states.get(sensor_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    async def async_added_to_hass(self) -> None:
        # Subscribe to PlantData listener updates (e.g. options changes)
        await super().async_added_to_hass()
        # Also subscribe directly to the underlying sensor so the entity
        # updates in real time with every new reading, not just when the
        # integration writes to options.
        sensor_id = self._plant.moisture_sensor
        if sensor_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [sensor_id], self._on_sensor_update
                )
            )

    @callback
    def _on_sensor_update(self, event) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Unavailable when no sensor is configured or the sensor is unavailable."""
        sensor_id = self._plant.moisture_sensor
        if not sensor_id:
            return False
        state = self._plant._hass.states.get(sensor_id)
        return state is not None and state.state not in ("unknown", "unavailable")
