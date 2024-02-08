"""Plaid integration"""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    Platform,
    CONF_NAME,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_TOKEN
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import Throttle

from .const import (
    API_ACCOUNTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)


#PLATFORM_SCHEMA = vol.Schema({
#    vol.Required(CONF_CLIENT_ID): cv.string,
#    vol.Required(CONF_CLIENT_SECRET): cv.string,
#    vol.Required(CONF_TOKEN): cv.string,
#    vol.Optional(CONF_NAME, None): cv.string
#})

CONFIG_SCHEMA = vol.Schema(
    cv.deprecated(DOMAIN),
    {
        DOMAIN: vol.Schema(
            {
                 vol.Required(CONF_CLIENT_ID): cv.string,
                 vol.Required(CONF_CLIENT_SECRET): cv.string,
                 vol.Required(CONF_TOKEN): cv.string,
                 vol.Optional(CONF_NAME, None): cv.string
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)

class PlaidData:
    """Get the latest data and update the states."""

    def __init__(self, config):
        """Init the plaid data object."""
        import plaid
        from plaid.api import plaid_api

        self.config = config
        self.available = False
        self.accounts = None
        self.transactions = None
        self.last_cursor = None
        self.access_token = config['access_token']
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox,
            api_key={
                'clientId': config['client_id'],
                'secret': config['secret'],
                'plaidVersion': '2020-09-14'
            }
        )
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from plaid."""
        account_data = get_accounts(self.client, self.access_token)
        if len(account_data) == 0:
            self.available = False
            return
        self.available = True
        self.accounts = account_data
        #transactions = get_transactions(self.headers, self.access_token, self.last_cursor)
        #self.transactions = transactions[0]
        #self.last_cursor = transactions[1]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Plaid component."""
    if DOMAIN not in config:
        return True
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plaid from a config entry."""

    instance = await hass.async_add_executor_job(create_and_update_instance, entry)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = instance

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def create_and_update_instance(entry: ConfigEntry) -> PlaidData:
    """Create and update a Plaid Data instance."""
    config = { 'client_id': entry.data[CONF_CLIENT_ID], 'secret': entry.data[CONF_CLIENT_SECRET], 'access_token': entry.data[CONF_TOKEN]}
    
    instance = PlaidData(config)
    instance.update()
    return instance


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""

    await hass.config_entries.async_reload(config_entry.entry_id)

    registry = entity_registry.async_get(hass)
    entities = entity_registry.async_entries_for_config_entry(
        registry, config_entry.entry_id
    )

    # Remove orphaned entities
    # for entity in entities:
    #     currency = entity.unique_id.split("-")[-1]
    #     if "xe" in entity.unique_id and currency not in config_entry.options.get(
    #         CONF_EXCHANGE_RATES, []
    #     ):
    #         registry.async_remove(entity.entity_id)
    #     elif "wallet" in entity.unique_id and currency not in config_entry.options.get(
    #         CONF_CURRENCIES, []
    #     ):
    #         registry.async_remove(entity.entity_id)


def get_accounts(client, access_token):
    """Handle paginated accounts."""
    import plaid
    from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
    request = AccountsBalanceGetRequest(
        access_token=access_token
    )

    try:
        response = client.accounts_balance_get(request)
        accounts = response.accounts

        return (True, accounts)
    except plaid.ApiException as e:
        _LOGGER.exception('Failed to get Plaid data: %s', e.body)
        return (False, [])


def get_transactions(headers, access_token, lastCursor=None):
    """Handle paginated accounts."""
    from requests import post
    data = { 'access_token': access_token }
    if lastCursor!=None:
        data['cursor']=lastCursor
    response = post('https://development.plaid.com/transactions/sync', headers=headers, json=data)
    responseJson = response.json()
    transactions = responseJson['added']
    if responseJson['has_more']:
        moreTransactions = get_transactions(headers,access_token,responseJson['next_cursor'])
        return (transactions + moreTransactions[0], moreTransactions[1])
    return (transactions, responseJson['next_cursor'])

