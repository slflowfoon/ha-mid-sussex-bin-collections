# Mid Sussex Bin Collections

A Home Assistant custom integration that retrieves future household waste
collection dates from the Mid Sussex District Council collection service.

The integration performs the council site's multi-step property lookup, updates
every six hours, and caches the last successful schedule. Cached dates remain
available if the collection website is temporarily unavailable.

## Entities

| Entity | Description |
| --- | --- |
| `sensor.mid_sussex_bin_collections_bin_collections` | Last refresh time, with all collection dates as attributes |
| `sensor.mid_sussex_bin_collections_next_rubbish_collection` | Next rubbish collection date |
| `sensor.mid_sussex_bin_collections_next_recycling_collection` | Next recycling collection date |
| `sensor.mid_sussex_bin_collections_next_garden_waste_collection` | Next garden waste collection date |
| `sensor.mid_sussex_bin_collections_next_food_waste_collection` | Next food waste collection date |

Home Assistant may append a suffix when an entity ID is already in use.

## Installation with HACS

1. Open HACS and add `slflowfoon/ha-mid-sussex-bin-collections` as a custom
   **Integration** repository.
2. Download **Mid Sussex Bin Collections**.
3. Restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**.
5. Search for **Mid Sussex Bin Collections** and enter the property details.

## Updating

Use `homeassistant.update_entity` on any entity from the integration to request
an immediate refresh. All entities share one coordinated request.

## Data source

This project is not affiliated with Mid Sussex District Council or Whitespace.
It reads the publicly available collection lookup at
`https://sms-wrp.whitespacews.com/`. Website changes may require parser updates.
