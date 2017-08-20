#!/usr/bin/env python
import argparse
import json

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
from investhor.utils import get_logger

# from bondora_api.rest import ApiException
CONFIG_FILE = "invest_primary.json"
logger = get_logger()


def buy_primary(bid_api, results, params):
    to_bid = []
    messages = []
    max_investment_per_loan = params.get("max_investment_per_loan", 50)
    max_amount = params.get("max_bid", 20)
    min_amount = params.get("min_bid", 1)
    min_gain = params.get("min_gain", 5)
    for res in results:
        target_discount = calculate_selling_discount(res)
        if target_discount < min_gain:
            continue
        if res.user_bid_amount >= max_investment_per_loan:
            continue
        if res.verification_type < 4:
            continue
        amount = min(max_amount, max_investment_per_loan - res.user_bid_amount)
        bid = Bid(auction_id=res.auction_id,
                  amount=amount,
                  min_amount=min_amount)
        to_bid.append(bid)
        message = "Bidding for:\n %s" % str(res)
        messages.append(message)
        logger.info(message)
    if to_bid:
        bid_request = BidRequest(to_bid)
        results = bid_api.bid_make_bids(bid_request)
        send_mail("Bidding from primary", "\n".join(messages))
    else:
        logger.info("No item to bid for in primary")
    return to_bid


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
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
