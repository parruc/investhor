#!/usr/bin/env python
import argparse
import json

from bondora_api import AccountApi
from bondora_api import SecondMarketApi
from bondora_api import configuration as bondora_configuration
from bondora_api.models import SecondMarketCancelRequest
from bondora_api.models import SecondMarketSaleRequest
from bondora_api.models import SecondMarketSell
from investhor.utils import add_next_payment_day_filters
from investhor.utils import calculate_selling_discount
from investhor.utils import load_config_file
from investhor.utils import oauth2_get_token
from investhor.utils import save_config_file
from investhor.utils import send_mail
from investhor.utils import get_logger

# from bondora_api.rest import ApiException
CONFIG_FILE = "sell_stale.json"
logger = get_logger()


def sell_items(secondary_api, results, cancel=False, rate=0):
    sell_requests = []
    cancel_requests = []
    messages = []
    for res in results.payload:
        if cancel:
            cancel_request.append(res)
            cancel_requests.append(cancel_request)
        sell_request = SecondMarketSell(loan_part_id=res.loan_part_id,
                                        desired_discount_rate=rate)
        sell_requests.append(sell_request)
        message = "Selling %s at 0%%", res.loan_part_id
        messages.append(message)
        logger.info(message)
    if to_cancel:
        cancel_request = SecondMarketCancelRequest([c.id for c in to_cancel])
        secondary_api.second_market_cancel_multiple(cancel_request)

    if sell_requests:
        sell_request = SecondMarketSaleRequest(sell_requests)
        send_mail("Selling stale", "\n".join(messages))
        return secondary_api.second_market_sell(sell_request)


def sell_items_not_in_secondary(secondary_api, params):
    account_api = AccountApi()
    request_params = params.copy()
    request_params["request_sales_status"] = 3
    request_params["request_loan_status_code"] = 2
    results = account_api.account_get_active(**request_params)
    if not results.payload:
        logger.info("No item to sell at 0% in your account")
    return sell_items(secondary_api, results)

def sell_items_already_in_secondary(secondary_api, params):
    request_params = params.copy()
    request_params["request_show_my_items"] = True
    results = secondary_api.second_market_get_active(**request_params)
    if not results.payload:
        logger.info("No item to sell at 0% in secondary market")
    return sell_items(secondary_api, results, cancel=True)

def main():
    params = load_config_file(CONFIG_FILE)
    request_params = params.copy()
    request_params = add_next_payment_day_filters(request_params)
    # Get only those that has next payment at least one month from now
    # Configure OAuth2 access token for authorization: oauth2
    # bondora_api.configuration.debug = True
    auth_token = oauth2_get_token()
    bondora_configuration.access_token = auth_token
    bondora_configuration.host = "https://api.bondora.com"
    # create an instance of the API class

    secondary_api = SecondMarketApi()
    results = sell_items_not_in_secondary(secondary_api, request_params)
    results = sell_items_already_in_secondary(secondary_api, request_params)
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
