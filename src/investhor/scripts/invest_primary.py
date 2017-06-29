#!/usr/bin/env python
import argparse
import json
import logging
from pprint import pprint

from bondora_api import AuctionApi
from bondora_api import BidApi
from bondora_api import SecondMarketApi
from bondora_api.models import Bid
from bondora_api.models import BidRequest
from bondora_api.models import SecondMarketBuyRequest
from bondora_api.models import SecondMarketSaleRequest
from bondora_api.models import SecondMarketSell
from investhor.utils import add_next_payment_day_filters
from investhor.utils import calculate_selling_discount
from investhor.utils import config
from investhor.utils import get_request_params
from investhor.utils import load_config_file
from investhor.utils import save_config_file
from investhor.utils import send_mail

# from bondora_api.rest import ApiException
CONFIG_FILE = "invest_primary.json"


def buy_primary(bid_api, results, params):
    to_bid = []
    messages = []
    max_investment_per_loan = getattr(params, "max_investment_per_loan", 50)
    max_amount = getattr(params, "max_bid", 20)
    min_amount = getattr(params, "min_bid", 1)
    min_gain = getattr(params, "min_gain", 5)
    for res in results:
        if target_discount - res.desired_discount_rate < min_gain:
            continue
        if res.user_bid_amount >= max_investment_per_loan:
            continue
        amount = min(max_amount, max_investment_per_loan - res.user_bid_amount)
        target_discount = calculate_selling_discount(res)
        bid = Bid(auction_id=res.auction_id,
                  amount=amount,
                  min_amount=min_amount)
        to_bid.append(bid)
        message = "Buying %s at %d%%" % (res.loan_part_id, res.desired_discount_rate)
        messages.append(message)
        logging.warning(message)
    if to_bid:
        bid_request = BidRequest([bid.id for bid in to_buy])
        results = bid_api.bid_make_bids(bid_request)
        pprint(to_bid)
        send_mail("buying from primary", "\n".join(messages))
    else:
        print("No item to buy in primary")
    return to_bid


def sell_primary(secondary_api, results):
    to_sell = []
    messages = []
    for res in results:
        target_discount = calculate_selling_discount(res)
        sell_request = SecondMarketSell(loan_part_id=res.loan_part_id,
                                        desired_discount_rate=target_discount)
        to_sell.append(sell_request)
        message = "Selling %s at %d%%" % (res.loan_part_id, target_discount)
        messages.append(message)
        logging.warning(message)
    if to_sell:
        sell_request = SecondMarketSaleRequest(to_sell)
        results = secondary_api.second_market_sell(sell_request)
        pprint(results.payload)
        send_mail("Selling from primary", "\n".join(messages))
    else:
        print("No item to sell from primary")
    return to_sell


def main():
    params = load_config_file(CONFIG_FILE)
    request_params = get_request_params(params)
    # Configure OAuth2 access token and other params
    config()
    # create an instance of the API class
    auction_api = AuctionApi()
    results = auction_api.auction_get_active(**request_params).payload
    bid_api = BidApi()
    results = buy_primary(bid_api, results, params)
    secondary_api = SecondMarketApi()
    results = sell_primary(secondary_api, results)
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
