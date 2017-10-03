#!/usr/bin/env python
import time

from bondora_api import AccountApi
from bondora_api import SecondMarketApi
from bondora_api.models import SecondMarketCancelRequest
from bondora_api.models import SecondMarketSaleRequest
from bondora_api.models import SecondMarketSell
from investhor.utils import calculate_selling_discount
from investhor.utils import config
from investhor.utils import get_investment_url
from investhor.utils import get_logger
from investhor.utils import get_request_params
from investhor.utils import load_config_file
from investhor.utils import save_config_file
from investhor.utils import send_mail

# from bondora_api.rest import ApiException
CONFIG_FILE = "sell_stale.json"
logger = get_logger()


def sell_items(secondary_api, results, on_sale, discount):
    to_sell = []
    to_cancel = []
    str_discount = discount * 100
    messages = []
    for res in results.payload:
        is_on_sale = False
        rate = calculate_selling_discount(res, discount=discount)
        for sale in on_sale.payload:
            if sale.loan_part_id == res.loan_part_id:
                is_on_sale = True
                if int(sale.desired_discount_rate) != rate:
                    to_cancel.append(sale.id)
                    to_sell.append(SecondMarketSell(
                        loan_part_id=res.loan_part_id,
                        desired_discount_rate=rate))
                break
        if not is_on_sale:
            to_sell.append(SecondMarketSell(loan_part_id=res.loan_part_id,
                           desired_discount_rate=rate))
    if to_cancel:
        chunks = [to_cancel[i:i+100] for i in range(0, len(to_cancel), 100)]
        for chunk in chunks:
            cancel_req = SecondMarketCancelRequest(to_cancel)
            results = secondary_api.second_market_cancel_multiple(cancel_req)
            for res in results.payload:
                msg = "Cancelling %s" % (get_investment_url(res))
                logger.info(msg)
                messages.append(msg)
            time.sleep(3)

    if to_sell:
        for chunk in [to_sell[i:i+100] for i in range(0, len(to_sell), 100)]:
            sell_req = SecondMarketSaleRequest(chunk)
            results = secondary_api.second_market_sell(sell_req)
            for res in results.payload:
                msg = "Selling %s at %d%%" % (get_investment_url(res), rate)
                logger.info(msg)
                messages.append(msg)
            time.sleep(3)
        send_mail("Selling with %d discount" % str_discount,
                  "\n".join(messages))
    else:
        logger.info("No item to sell at %d%% discount in your account" %
                    str_discount)
    return to_sell


def sell_items_in_account(secondary_api, params, discount):
    account_api = AccountApi()
    request_params = params.copy()
    request_params["request_loan_status_code"] = 2
    results = account_api.account_get_active(**request_params)
    request_params = params.copy()
    request_params["request_show_my_items"] = True
    on_sale = secondary_api.second_market_get_active(**request_params)
    return sell_items(secondary_api, results, on_sale, discount)


def main():
    params = load_config_file(CONFIG_FILE)
    # Configure OAuth2 access token and other params
    config()
    # create an instance of the API class
    secondary_api = SecondMarketApi()
    for discount_name in ["no", "low", "medium", "high", "crazy", "total"]:
        discount_name += "_discount"
        discount = params[discount_name]
        for bound in ["max_days_till_next_payment",
                      "min_days_till_next_payment"]:
            if bound in params:
                del(params[bound])
            key = "_".join((bound, discount_name))
            if key in params:
                params[bound] = params[key]
        request_params = get_request_params(params)
        sell_items_in_account(secondary_api, request_params, discount)

    for bound in ["max_days_till_next_payment", "min_days_till_next_payment"]:
        if bound in params:
            del(params[bound])
    save_config_file(params, CONFIG_FILE)


if __name__ == "__main__":
    # execute only if run as a script
    main()
