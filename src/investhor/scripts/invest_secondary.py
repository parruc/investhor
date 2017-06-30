#!/usr/bin/env python
import argparse
import json

from bondora_api import SecondMarketApi
from bondora_api import configuration as bondora_configuration
from bondora_api.models import SecondMarketBuyRequest
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
CONFIG_FILE = "invest_secondary.json"
logger = get_logger()

def buy_secondary(secondary_api, results, min_gain):
    to_buy = []
    messages = []
    for res in results:
        target_discount = calculate_selling_discount(res)
        if target_discount - res.desired_discount_rate > min_gain:
            to_buy.append(res)
            message = "Buying %s at %d%%" % (res.loan_part_id, res.desired_discount_rate)
            messages.append(message)
            logger.info(message)
    if to_buy:
        buy_request = SecondMarketBuyRequest([buy.id for buy in to_buy])
        secondary_api.second_market_buy(buy_request)
        send_mail("Buying from secondary", "\n".join(messages))
    else:
        logger.info("No item to buy in secondary")
    return to_buy


def sell_secondary(secondary_api, results):
    to_sell = []
    messages = []
    for res in results:
        target_discount = calculate_selling_discount(res)
        sell_request = SecondMarketSell(loan_part_id=res.loan_part_id,
                                        desired_discount_rate=target_discount)
        to_sell.append(sell_request)
        message = "Selling %s at %d%%" % (res.loan_part_id, target_discount)
        messages.append(message)
        logger.info(message)
    if to_sell:
        sell_request = SecondMarketSaleRequest(to_sell)
        results = secondary_api.second_market_sell(sell_request)
        send_mail("Selling from secondary", "\n".join(messages))
    else:
        logger.info("No item to sell in secondary")
    return to_sell


def main():
    params = load_config_file(CONFIG_FILE)
    request_params = params.copy()
    # Get only those that has next payment at least one month from now
    request_params = add_next_payment_day_filters(request_params)
    # Configure OAuth2 access token for authorization: oauth2
    # bondora_api.configuration.debug = True
    auth_token = oauth2_get_token()
    bondora_configuration.access_token = auth_token
    bondora_configuration.host = "https://api.bondora.com"
    # create an instance of the API class
    secondary_api = SecondMarketApi()
    request_params = {k: v for k, v in request_params.items() if k.startswith("request_")}
    results = secondary_api.second_market_get_active(**request_params).payload
    results = buy_secondary(secondary_api, results, params["min_percentage_overhead"])
    results = sell_secondary(secondary_api, results)
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
