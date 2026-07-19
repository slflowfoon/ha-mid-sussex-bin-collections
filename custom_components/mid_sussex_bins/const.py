"""Constants for the Mid Sussex Bin Collections integration."""

from datetime import timedelta

DOMAIN = "mid_sussex_bins"

CONF_PROPERTY_NUMBER = "property_number"
CONF_STREET_NAME = "street_name"

BASE_URL = "https://sms-wrp.whitespacews.com/"
UPDATE_INTERVAL = timedelta(hours=6)

COLLECTION_TYPES = ("rubbish", "recycling", "garden", "food")
