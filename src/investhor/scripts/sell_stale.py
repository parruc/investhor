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
from investhor.utils import config
from investhor.utils import save_config_file
from investhor.utils import send_mail
from investhor.utils import get_investment_url
from investhor.utils import get_logger
from investhor.utils import get_request_params

# from bondora_api.rest import ApiException
CONFIG_FILE = "sell_stale.json"
logger = get_logger()


def sell_items(secondary_api, results, cancel=False, calculate_rate=False):
    to_sell = []
    to_cancel = []
    messages = []
    for res in results.payload:
        rate = 0
        if calculate_rate:
            rate = calculate_selling_discount(res)
        if cancel:
            to_cancel.append(res)
        to_sell.append(SecondMarketSell(loan_part_id=res.loan_part_id,
                                        desired_discount_rate=rate))
        message = "Selling %s at %d%%" % (get_investment_url(res), rate)
        messages.append(message)
        logger.info(message)
    if to_cancel:
        cancel_request = SecondMarketCancelRequest([c.id for c in to_cancel])
        secondary_api.second_market_cancel_multiple(cancel_request)
    if to_sell:
        sell_request = SecondMarketSaleRequest(to_sell)
        results = secondary_api.second_market_sell(sell_request)
    return to_sell


def sell_items_not_on_sale(secondary_api, params):
    account_api = AccountApi()
    request_params = params.copy()
    if "request_next_payment_date_from" in request_params:
        del(request_params["request_next_payment_date_from"])
    if "request_next_payment_date_to" in request_params:
        del(request_params["request_next_payment_date_to"])
    request_params["request_sales_status"] = 3
    request_params["request_loan_status_code"] = 2
    results = account_api.account_get_active(**request_params)
    if not results.payload:
        logger.info("No item to sell at market price in your account")
    return sell_items(secondary_api, results, calculate_rate=True)


def sell_stale_items_not_on_sale(secondary_api, params):
    account_api = AccountApi()
    request_params = params.copy()
    request_params["request_sales_status"] = 3
    request_params["request_loan_status_code"] = 2
    results = account_api.account_get_active(**request_params)
    if not results.payload:
        logger.info("No item to sell at 0% in your account")
    return sell_items(secondary_api, results)

def sell_stale_items_on_sale(secondary_api, params):
    request_params = params.copy()
    request_params["request_show_my_items"] = True
    results = secondary_api.second_market_get_active(**request_params)
    if not results.payload:
        logger.info("No item to sell at 0% in secondary market")
    return sell_items(secondary_api, results, cancel=True)

def main():
    params = load_config_file(CONFIG_FILE)
    request_params = get_request_params(params)
    # Configure OAuth2 access token and other params
    config()
    # create an instance of the API class
    secondary_api = SecondMarketApi()
    results = sell_stale_items_not_on_sale(secondary_api, request_params)
    results = sell_stale_items_on_sale(secondary_api, request_params)
    results = sell_items_not_on_sale(secondary_api, request_params)
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
