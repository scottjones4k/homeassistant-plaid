"""Support for Plaid sensors."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    API_ACCOUNT_ID
)

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Plaid"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plaid sensor platform."""
    instance = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SensorEntity] = []

    for account in instance.accounts:
        entities.append(AccountSensor(instance, account.mask))
    async_add_entities(entities)


class AccountSensor(SensorEntity):
    """Representation of a Plaid sensor."""

    def __init__(self, plaid_data, mask):
        """Initialize the sensor."""
        self._plaid_data = plaid_data
        self._mask = mask
        for account in self._plaid_data.accounts:
            if (
                account.mask == self._mask
            ):
                self._name = f"{account.name} Balance"
                self._id = (
                    f"plaid-{account.account_id}"
                )
                self._state = account.balances.available
                self._unit_of_measurement = account.balances.iso_currency_code
                self._current_balance = account.balances.current
                self._balance_limit = account.balances.limit
                
                addedTransactions = list(filter(lambda t: t[API_ACCOUNT_ID] == account[API_ACCOUNT_ID], self._plaid_data.transactions))
                addedTransactions.sort(key=lambda t: t['datetime'], reverse=True) #newest first
                self._transactions = list(map(map_transaction, addedTransactions[:10]))
                break
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def available(self):
        """Return the name of the sensor."""
        return self._plaid_data.available

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the Unique ID of the sensor."""
        return self._id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return DEFAULT_COIN_ICON

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'Current Balance': self._current_balance,
            'Balance Limit': self._balance_limit,
            'Mask': self._mask,
            'Transactions': self._transactions
        }

    def update(self):
        """Get the latest state of the sensor."""
        self._plaid_data.update()
        for account in self._plaid_data.accounts:
            if (
                account.mask == self._mask
            ):
                self._name = f"Plaid {account.name}"
                self._id = (
                    f"plaid-{account.account_id}"
                )
                self._state = account.balances.available
                self._unit_of_measurement = account.balances.iso_currency_code
                self._current_balance = account.balances.current
                self._balance_limit = account.balances.limit
                
                addedTransactions = self._transactions + list(map(map_transaction, list(filter(lambda t: t[API_ACCOUNT_ID] == account[API_ACCOUNT_ID], self._plaid_data.transactions))))
                
                transactions = []
                for t in addedTransactions:
                    if all(tr['Transaction Id'] != t['Transaction Id'] for tr in transactions):
                        transactions.append(t)
                transactions.sort(key=lambda t: t['Date Time'], reverse=True) #newest first
                
                self._transactions = transactions[:10]
                break

def map_transaction(transaction):
    return {
        'Amount': transaction['amount'],
        'Name': transaction['name'],
        'Currency': transaction['iso_currency_code'],
        'Date Time': transaction['datetime'],
        'Type': transaction['transaction_code'],
        'Pending': transaction['pending'],
        'Transaction Id': transaction['transaction_id']
    }
    
