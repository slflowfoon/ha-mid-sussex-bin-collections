"""Client and parsers for the Mid Sussex waste collection service."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .const import BASE_URL, COLLECTION_TYPES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": BASE_URL,
}

COLLECTION_KEYWORDS = {
    "rubbish": ("refuse", "rubbish"),
    "recycling": ("recycling",),
    "garden": ("garden",),
    "food": ("food",),
}


class BinCollectionError(Exception):
    """Base error for the waste collection service."""


class CannotConnect(BinCollectionError):
    """Raised when the waste collection service cannot be reached."""


class AddressNotFound(BinCollectionError):
    """Raised when the configured property cannot be found."""


class InvalidResponse(BinCollectionError):
    """Raised when the service returns an unexpected page."""


@dataclass(frozen=True, slots=True)
class BinCollectionData:
    """The next collection date for each supported waste type."""

    collections: dict[str, date | None]
    last_updated: datetime
    address: str
    cached: bool = False

    def with_cached(self, cached: bool) -> BinCollectionData:
        """Return a copy with the cache marker changed."""
        return replace(self, cached=cached)

    def as_storage_dict(self) -> dict[str, Any]:
        """Serialize data for Home Assistant storage."""
        return {
            "collections": {
                key: value.isoformat() if value is not None else None
                for key, value in self.collections.items()
            },
            "last_updated": self.last_updated.isoformat(),
            "address": self.address,
        }

    @classmethod
    def from_storage_dict(cls, value: dict[str, Any]) -> BinCollectionData:
        """Restore data from Home Assistant storage."""
        stored_collections = value.get("collections", {})
        collections = {
            key: (
                date.fromisoformat(stored_collections[key])
                if stored_collections.get(key)
                else None
            )
            for key in COLLECTION_TYPES
        }
        last_updated = datetime.fromisoformat(value["last_updated"])
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=UTC)
        return cls(
            collections=collections,
            last_updated=last_updated,
            address=str(value.get("address", "")),
            cached=True,
        )


def _normalise_address(value: str) -> str:
    """Normalise address text for reliable matching."""
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", value.upper()).split())


def _find_link(soup: BeautifulSoup, text: str, base_url: str) -> str | None:
    """Find a link by visible text and return an absolute URL."""
    text = text.casefold()
    for link in soup.find_all("a", href=True):
        if text in link.get_text(" ", strip=True).casefold():
            return urljoin(base_url, str(link["href"]))
    return None


def _select_address_link(
    html: str,
    base_url: str,
    property_number: str,
    street_name: str,
    postcode: str,
) -> tuple[str, str]:
    """Select the exact address returned by the property lookup."""
    soup = BeautifulSoup(html, "html.parser")
    target_prefix = _normalise_address(f"{property_number} {street_name}")
    postcode_compact = re.sub(r"\s+", "", postcode.upper())

    prefix_matches: list[tuple[str, str, bool]] = []
    for link in soup.find_all("a", href=True):
        label = link.get_text(" ", strip=True)
        normalised = _normalise_address(label)
        if not normalised.startswith(target_prefix):
            continue
        contains_postcode = postcode_compact in normalised.replace(" ", "")
        prefix_matches.append(
            (urljoin(base_url, str(link["href"])), label, contains_postcode)
        )

    if not prefix_matches:
        raise AddressNotFound("The configured property was not returned by the lookup")

    postcode_matches = [match for match in prefix_matches if match[2]]
    candidates = postcode_matches or prefix_matches
    if len(candidates) != 1:
        raise AddressNotFound(
            "The property lookup returned more than one matching address"
        )

    return candidates[0][0], candidates[0][1]


def _parse_collection_page(
    html: str,
    today: date,
    address: str,
) -> BinCollectionData:
    """Parse the next collection date for each waste type."""
    soup = BeautifulSoup(html, "html.parser")
    collections: dict[str, date | None] = dict.fromkeys(COLLECTION_TYPES)
    parsed_rows = 0

    for collection_list in soup.select("ul.displayinlineblock"):
        items = collection_list.find_all("li")
        if len(items) < 3:
            continue

        try:
            collection_date = datetime.strptime(
                items[1].get_text(" ", strip=True), "%d/%m/%Y"
            ).date()
        except ValueError:
            continue

        if collection_date < today:
            continue

        collection_type = items[2].get_text(" ", strip=True).casefold()
        for key, keywords in COLLECTION_KEYWORDS.items():
            if not any(keyword in collection_type for keyword in keywords):
                continue
            current = collections[key]
            if current is None or collection_date < current:
                collections[key] = collection_date
            parsed_rows += 1
            break

    if parsed_rows == 0:
        raise InvalidResponse("No future collection dates were found")

    return BinCollectionData(
        collections=collections,
        last_updated=datetime.now(UTC),
        address=address,
    )


class MidSussexBinsClient:
    """Asynchronous client for the Mid Sussex collection lookup."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        property_number: str,
        street_name: str,
        postcode: str,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._property_number = property_number.strip().upper()
        self._street_name = street_name.strip().upper()
        self._postcode = postcode.strip().upper()

    async def _async_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> tuple[str, str]:
        """Request one page and return its final URL and body."""
        try:
            async with self._session.request(
                method,
                url,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
                **kwargs,
            ) as response:
                response.raise_for_status()
                return str(response.url), await response.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise CannotConnect(f"Unable to request {url}: {err}") from err

    async def async_get_collections(self) -> BinCollectionData:
        """Run the property lookup and fetch its collection calendar."""
        main_url, main_html = await self._async_request("GET", BASE_URL)
        collection_link = _find_link(
            BeautifulSoup(main_html, "html.parser"),
            "View my collections",
            main_url,
        )
        if collection_link is None:
            raise InvalidResponse("The collection lookup link was not found")

        form_url, form_html = await self._async_request("GET", collection_link)
        form_soup = BeautifulSoup(form_html, "html.parser")
        form = form_soup.find("form", attrs={"data-form-title": "Property Lookup Form"})
        if form is None or not form.get("action"):
            raise InvalidResponse("The property lookup form was not found")

        lookup_url = urljoin(form_url, str(form["action"]))
        result_url, result_html = await self._async_request(
            "POST",
            lookup_url,
            data={
                "address_name_number": self._property_number,
                "address_street": self._street_name,
                "address_postcode": self._postcode,
                "street_town": "",
            },
        )

        calendar_url, address = _select_address_link(
            result_html,
            result_url,
            self._property_number,
            self._street_name,
            self._postcode,
        )
        _, calendar_html = await self._async_request("GET", calendar_url)
        return _parse_collection_page(calendar_html, date.today(), address)
