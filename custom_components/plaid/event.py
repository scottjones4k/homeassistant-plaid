"""Support for Plaid sensors."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    API_ACCOUNT_ID
)

from homeassistant.components.event import (
    ENTITY_ID_FORMAT,
    EventDeviceClass,
    EventEntity,
)

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Plaid"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Plaid event entities."""
    instance = hass.data[DOMAIN][entry.entry_id]

    entities: list[PlaidTransactionEventEntity] = []

    for account in instance.accounts:
        entities.append(PlaidTransactionEventEntity(instance, account))
    async_add_entities(entities)


class PlaidTransactionEventEntity(EventEntity):
    """Representation of a Plaid Event Entity."""

    def __init__(self, plaid_data, account):
        """Initialize the sensor."""
        mask = account.mask
        self._plaid_data = plaid_data
        self._mask = mask
        self._account_id = account.account_id

        self.entity_id = ENTITY_ID_FORMAT.format(f"plaid-{account.name}-transactions")

        self._button = mask

        self._attr_name = f"{account.name} Transactions"
        self._attr_event_types = ['adjustment', 'atm', 'bank charge', 'bill payment', 'cash', 'cashback', 'cheque', 'direct debit', 'interest', 'purchase', 'standing order', 'transfer']
        self._attr_unique_id = self.entity_id

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()

        # Register event callback
        self._plaid_data.register_event(
            self._account_id, self._event_callback
        )

    def _event_callback(self, transaction) -> None:
        _LOGGER.debug("Transaction event fired %s: %s", transaction.account_id, self._account_id)
        if transaction.account_id == self._account_id:
            self._trigger_event(str(transaction.transaction_code), map_transaction(transaction))
            self.schedule_update_ha_state()

def map_transaction(transaction):
    return {
        'Amount': transaction['amount'],
        'Name': transaction['name'],
        'Currency': transaction['iso_currency_code'],
        'Date Time': transaction['datetime'],
        'Type': str(transaction['transaction_code']),
        'Pending': transaction['pending'],
        'Transaction Id': transaction['transaction_id']
    }