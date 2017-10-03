#!/usr/bin/env python
import operator

from bondora_api import SecondMarketApi
from bondora_api.models import SecondMarketBuyRequest
from investhor.utils import calculate_selling_discount
from investhor.utils import config
from investhor.utils import get_investment_url
from investhor.utils import get_logger
from investhor.utils import get_request_params
from investhor.utils import load_config_file
from investhor.utils import save_config_file
from investhor.utils import send_mail

# from bondora_api.rest import ApiException
CONFIG_FILE = "invest_secondary.json"
logger = get_logger()


def buy_secondary(secondary_api, results, params):
    to_buy = []
    messages = []
    min_gain = params.get("min_percentage_overhead", 6)
    max_investment_per_loan = params.get("max_investment_per_loan", 50)
    for res in results:
        target_discount = calculate_selling_discount(res)
        if res.user_bid_amount >= max_investment_per_loan:
            continue
        if target_discount - res.desired_discount_rate < min_gain:
            continue
        if res.next_payment_nr > 1:
            continue
        to_buy.append(res)
    if to_buy:
        to_buy.sort(key=operator.attrgetter('xirr', 'desired_discount_rate'))
        buy_request = SecondMarketBuyRequest([buy.id for buy in to_buy])
        bought = secondary_api.second_market_buy(buy_request)
        for b in bought.payload:
            message = "Buying at %d%%:\n\t%s\n(%s)" % (b.desired_discount_rate,
                                                       str(b),
                                                       get_investment_url(b),)
            messages.append(message)
            logger.info(message)
        send_mail("Buying from secondary", "\n".join(messages))
    else:
        logger.info("No item to buy in secondary")
    return to_buy


def main():
    params = load_config_file(CONFIG_FILE)
    request_params = get_request_params(params)
    # Configure OAuth2 access token and other params
    config()
    # create an instance of the API class
    secondary_api = SecondMarketApi()
    results = secondary_api.second_market_get_active(**request_params).payload
    results = buy_secondary(secondary_api, results, params)
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
