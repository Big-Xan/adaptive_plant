"""Select entity for plant health status."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HEALTH_OPTIONS
from .plant import PlantData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    plant: PlantData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HealthSelect(plant, entry)])


class HealthSelect(SelectEntity):
    """Select entity representing the current health status of a plant."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "health"
    _attr_options = HEALTH_OPTIONS
    _attr_icon = "mdi:leaf"

    def __init__(self, plant: PlantData, entry: ConfigEntry) -> None:
        self._plant = plant
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_health"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._plant.plant_name,
            manufacturer="Adaptive Plant",
            model="Plant Monitor",
        )

    @property
    def current_option(self) -> str:
        return self._plant.health

    @property
    def extra_state_attributes(self) -> dict:
        """Expose health timing data for the companion card overdue indicator."""
        return {
            "health_last_updated": self._plant.health_last_updated,
            "health_prompt_interval": self._plant.health_prompt_interval,
            "health_check_in_overdue": self._plant.health_check_in_overdue,
        }

    async def async_added_to_hass(self) -> None:
        self._plant.add_listener(self._on_plant_update)

    async def async_will_remove_from_hass(self) -> None:
        self._plant.remove_listener(self._on_plant_update)

    @callback
    def _on_plant_update(self) -> None:
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        await self._plant.set_health(option)
