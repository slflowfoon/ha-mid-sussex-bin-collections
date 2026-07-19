"""Data coordinator for Mid Sussex Bin Collections."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BinCollectionData, BinCollectionError, MidSussexBinsClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


class MidSussexBinsCoordinator(DataUpdateCoordinator[BinCollectionData]):
    """Fetch and cache waste collection dates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        client: MidSussexBinsClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.entry_id = entry_id
        self._store = Store[dict](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
        )

    async def async_load_cached_data(self) -> None:
        """Load the last successful schedule before the first network request."""
        stored = await self._store.async_load()
        if not stored:
            return
        try:
            self.data = BinCollectionData.from_storage_dict(stored)
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Ignoring invalid cached bin collection data")

    async def _async_update_data(self) -> BinCollectionData:
        """Fetch the current collection schedule."""
        try:
            data = await self.client.async_get_collections()
        except BinCollectionError as err:
            raise UpdateFailed(str(err)) from err

        await self._store.async_save(data.as_storage_dict())
        return data
