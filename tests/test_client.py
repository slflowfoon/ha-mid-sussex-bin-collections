"""Tests for the Mid Sussex waste collection parser."""

import sys
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType

# Load the parser package without importing Home Assistant-specific __init__.py.
PACKAGE_NAME = "custom_components.mid_sussex_bins"
package = ModuleType(PACKAGE_NAME)
package.__path__ = [
    str(Path(__file__).parents[1] / "custom_components" / "mid_sussex_bins")
]
sys.modules[PACKAGE_NAME] = package

from custom_components.mid_sussex_bins.client import (  # noqa: E402
    AddressNotFound,
    BinCollectionData,
    _parse_collection_page,
    _select_address_link,
)


class AddressSelectionTests(unittest.TestCase):
    """Address selection tests."""

    def test_selects_exact_property(self) -> None:
        """Select an exact number, street and postcode match."""
        html = """
        <a href="/wrong">132, EXAMPLE ROAD, TESTVILLE, AB1 2CD</a>
        <a href="/right">32, EXAMPLE ROAD, TESTVILLE, AB1 2CD</a>
        """
        url, label = _select_address_link(
            html,
            "https://example.test/search",
            "32",
            "EXAMPLE ROAD",
            "AB1 2CD",
        )
        self.assertEqual(url, "https://example.test/right")
        self.assertEqual(label, "32, EXAMPLE ROAD, TESTVILLE, AB1 2CD")

    def test_rejects_missing_property(self) -> None:
        """Reject a lookup that does not contain the property."""
        with self.assertRaises(AddressNotFound):
            _select_address_link(
                '<a href="/wrong">31, EXAMPLE ROAD, AB1 2CD</a>',
                "https://example.test/search",
                "32",
                "EXAMPLE ROAD",
                "AB1 2CD",
            )


class CollectionParsingTests(unittest.TestCase):
    """Collection page parsing tests."""

    def test_returns_earliest_future_date_per_type(self) -> None:
        """Ignore past dates and retain the next future collection."""
        html = "".join(
            (
                '<ul class="displayinlineblock"><li>x</li>'
                "<li>18/07/2026</li><li>Refuse</li></ul>",
                '<ul class="displayinlineblock"><li>x</li>'
                "<li>31/07/2026</li><li>Refuse Collection</li></ul>",
                '<ul class="displayinlineblock"><li>x</li>'
                "<li>24/07/2026</li><li>Mixed Recycling</li></ul>",
                '<ul class="displayinlineblock"><li>x</li>'
                "<li>25/07/2026</li><li>Food Waste</li></ul>",
                '<ul class="displayinlineblock"><li>x</li>'
                "<li>30/07/2026</li><li>Garden Waste</li></ul>",
            )
        )
        result = _parse_collection_page(
            html,
            date(2026, 7, 19),
            "32, EXAMPLE ROAD",
        )
        self.assertEqual(result.collections["rubbish"], date(2026, 7, 31))
        self.assertEqual(result.collections["recycling"], date(2026, 7, 24))
        self.assertEqual(result.collections["food"], date(2026, 7, 25))
        self.assertEqual(result.collections["garden"], date(2026, 7, 30))

    def test_storage_round_trip_marks_data_cached(self) -> None:
        """Cached schedules retain dates and are marked as cached."""
        html = (
            '<ul class="displayinlineblock"><li>x</li>'
            "<li>31/07/2026</li><li>Refuse</li></ul>"
        )
        result = _parse_collection_page(
            html,
            date(2026, 7, 19),
            "32, EXAMPLE ROAD",
        )
        restored = BinCollectionData.from_storage_dict(result.as_storage_dict())
        self.assertEqual(restored.collections, result.collections)
        self.assertEqual(restored.last_updated, result.last_updated)
        self.assertTrue(restored.cached)


if __name__ == "__main__":
    unittest.main()
