"""Config flow for Mid Sussex Bin Collections."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    AddressNotFound,
    CannotConnect,
    InvalidResponse,
    MidSussexBinsClient,
)
from .const import CONF_POSTCODE, CONF_PROPERTY_NUMBER, CONF_STREET_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)
POSTCODE_PATTERN = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$",
    re.IGNORECASE,
)


def _normalise_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Normalize values stored in the config entry."""
    return {
        CONF_PROPERTY_NUMBER: str(user_input[CONF_PROPERTY_NUMBER]).strip().upper(),
        CONF_STREET_NAME: str(user_input[CONF_STREET_NAME]).strip().upper(),
        CONF_POSTCODE: str(user_input[CONF_POSTCODE]).strip().upper(),
    }


def _location_id(data: dict[str, str]) -> str:
    """Build a stable, non-secret unique ID for one property."""
    postcode = re.sub(r"\s+", "", data[CONF_POSTCODE])
    street = re.sub(r"\s+", " ", data[CONF_STREET_NAME])
    return f"{postcode}:{street}:{data[CONF_PROPERTY_NUMBER]}".casefold()


class MidSussexBinsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Mid Sussex Bin Collections config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Validate a property and create its config entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalise_input(user_input)
            if not POSTCODE_PATTERN.fullmatch(data[CONF_POSTCODE]):
                errors[CONF_POSTCODE] = "invalid_postcode"
            else:
                client = MidSussexBinsClient(
                    async_get_clientsession(self.hass),
                    data[CONF_PROPERTY_NUMBER],
                    data[CONF_STREET_NAME],
                    data[CONF_POSTCODE],
                )
                try:
                    result = await client.async_get_collections()
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except AddressNotFound:
                    errors["base"] = "address_not_found"
                except InvalidResponse:
                    errors["base"] = "invalid_response"
                except Exception:
                    _LOGGER.exception("Unexpected error validating the property")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(_location_id(data))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=result.address, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_PROPERTY_NUMBER): str,
                vol.Required(CONF_STREET_NAME): str,
                vol.Required(CONF_POSTCODE): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
