"""Sensors for Mid Sussex Bin Collections."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import MidSussexBinsCoordinator

COLLECTION_SENSORS = {
    "rubbish": ("Next Rubbish Collection", "next_rubbish_collection", "mdi:trash-can"),
    "recycling": (
        "Next Recycling Collection",
        "next_recycling_collection",
        "mdi:recycle",
    ),
    "garden": (
        "Next Garden Waste Collection",
        "next_garden_waste_collection",
        "mdi:leaf",
    ),
    "food": (
        "Next Food Waste Collection",
        "next_food_waste_collection",
        "mdi:food-apple",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up collection sensors."""
    coordinator: MidSussexBinsCoordinator = entry.runtime_data
    async_add_entities(
        [
            BinCollectionsSummarySensor(coordinator),
            *(
                BinCollectionDateSensor(coordinator, key, *description)
                for key, description in COLLECTION_SENSORS.items()
            ),
        ]
    )


class MidSussexBinsEntity(CoordinatorEntity[MidSussexBinsCoordinator], SensorEntity):
    """Base entity for a configured property."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: MidSussexBinsCoordinator, key: str) -> None:
        """Initialize a collection entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry_id)},
            name="Mid Sussex Bin Collections",
            manufacturer="Mid Sussex District Council",
            model="Waste collection schedule",
            configuration_url=BASE_URL,
        )

    @property
    def available(self) -> bool:
        """Keep cached data available when a refresh fails."""
        return self.coordinator.data is not None

    @property
    def _source_attributes(self) -> dict[str, Any]:
        """Return common source and freshness attributes."""
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "address": data.address,
            "source": BASE_URL,
            "data_source": (
                "cache"
                if data.cached or not self.coordinator.last_update_success
                else "live"
            ),
            "last_updated": data.last_updated.isoformat(),
        }


class BinCollectionsSummarySensor(MidSussexBinsEntity):
    """Compatibility sensor containing all collection dates as attributes."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:trash-can"
    _attr_name = "Bin Collections Last Updated"
    _attr_suggested_object_id = "last_updated"

    def __init__(self, coordinator: MidSussexBinsCoordinator) -> None:
        """Initialize the summary sensor."""
        super().__init__(coordinator, "bin_collections")

    @property
    def native_value(self) -> datetime | None:
        """Return when the schedule was last refreshed."""
        return self.coordinator.data.last_updated if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return collection dates using the legacy MQTT attribute names."""
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            **{
                key: value.isoformat() if value is not None else None
                for key, value in data.collections.items()
            },
            **self._source_attributes,
        }


class BinCollectionDateSensor(MidSussexBinsEntity):
    """Sensor representing the next date for one collection type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: MidSussexBinsCoordinator,
        key: str,
        name: str,
        object_id: str,
        icon: str,
    ) -> None:
        """Initialize a date sensor."""
        super().__init__(coordinator, key)
        self._key = key
        self._attr_name = name
        self._attr_suggested_object_id = object_id
        self._attr_icon = icon

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.collections.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source attributes."""
        return self._source_attributes
