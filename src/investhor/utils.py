from datetime import datetime
from datetime import timedelta
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.utils import make_msgid
import json
import logging
import math
import os
import smtplib
import sys

from bondora_api import configuration as bondora_configuration
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

OAUTH_CONFIG_FILE = "oauth2.json"
EMAIL_CONFIG_FILE = "email.json"


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def get_investment_url(res):
    base_url = "https://www.bondora.com/en/investments?search=search&InvestmentSearch.InvestmentNumberOnly="
    investment_number = "%d-%d" % (res.auction_number, res.auction_bid_number)
    return base_url + investment_number

def send_mail(subject, text):
    params = load_config_file(EMAIL_CONFIG_FILE)
    smtp_user = params.get("smtp_user", "")
    smtp_pass = params.get("smtp_pass", "")
    smtp_host = params.get("smtp_host", "")
    smtp_port = params.get("smtp_port", "")
    mail_to = params.get("mail_to", "")
    if smtp_user and smtp_pass and smtp_host and smtp_port and mail_to:
        mail_from = params.get("mail_from", smtp_user)
        subject_prefix = params.get("subject_prefix", "")
        if subject_prefix:
            subject = subject_prefix + " " + subject
        # Create the base text message.
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = [mail_to, ]
        msg.set_content(text)
        s = smtplib.SMTP_SSL(smtp_host + ":" + smtp_port)
        s.login(smtp_user, smtp_pass)
        s.sendmail(mail_from, mail_to, msg.as_string())
        s.quit()
    else:
        logging.error("Cannot send email, some param missing")


def get_request_params(params):
    request_params = params.copy()
    # Get only those that has next payment at least one month from now
    request_params = add_next_payment_day_filters(request_params)
    request_params = {k: v for k, v in request_params.items() if k.startswith("request_")}
    return request_params


def get_config_file_path(file_name):
    script_dir = os.path.dirname(__file__)
    return os.path.join(script_dir, "config", file_name)


def load_config_file(file_name):
    """Reads configuration from 'file_path' file
    """
    file_path = get_config_file_path(file_name)
    with open(file_path) as config_file:
        return json.load(config_file)


def calculate_selling_discount(result):
    """ Calculates the discount based on investment interest and risk
    """
    if result.interest > 100:
        discount = math.floor(result.interest/20)
    elif result.interest > 50:
        discount = math.floor(result.interest/15)
    else:
        discount = max(1, math.floor(result.interest/10))
    if result.income_verification_status == 4:
        discount += 2
    elif result.income_verification_status > 1:
        discount += 1
    return discount


def save_config_file(params, file_name):
    """Save last working params to 'file_path' file
    """
    file_path = get_config_file_path(file_name)
    with open(file_path, "w") as out_file:
        json.dump(params, out_file, sort_keys=True, indent=4)


def add_next_payment_day_filters(params):
    if "min_days_till_next_payment" in params:
        min_days = timedelta(params["min_days_till_next_payment"])
        future_date = datetime.today() + min_days
        params["request_next_payment_date_from"] = future_date.isoformat()
        del(params["min_days_till_next_payment"])
    if "max_days_till_next_payment" in params:
        max_days = timedelta(params["max_days_till_next_payment"])
        future_date = datetime.today() + max_days
        params["request_next_payment_date_to"] = future_date.isoformat()
        del(params["max_days_till_next_payment"])
    return params


def config(debug=False):
    """Requests and sets up the token and other config params
    """
    auth_token = oauth2_get_token()
    if debug:
        bondora_api.configuration.debug = True
    bondora_configuration.access_token = auth_token
    bondora_configuration.host = "https://api.bondora.com"


def oauth2_get_token():
    """Get an oauth2 auth_token for the app to work. May need app approval
    """
    params = load_config_file(OAUTH_CONFIG_FILE)
    oauth = OAuth2Session(params["client_id"], scope=params["scope"])
    token_expires = datetime.utcfromtimestamp(params.get("expires_at", 0))
    refresh = (token_expires - datetime.now()).days < 2
    if "access_token" not in params:
        authorization_url, state = oauth.authorization_url(params["auth_url"])
        print('Please go to %s and authorize access.' % authorization_url)
        authorization_response = input('Paste the full redirect URL here:')
        token = oauth.fetch_token(
            params["token_url"],
            authorization_response=authorization_response,
            client_secret=params["client_secret"])
        params.update(token)
        save_config_file(params, OAUTH_CONFIG_FILE)
    elif refresh:
        token = oauth.refresh_token(params["token_url"],
                                    client_id=params["client_id"],
                                    client_secret=params["client_secret"],
                                    refresh_token=params["refresh_token"])
        params.update(token)
        save_config_file(params, OAUTH_CONFIG_FILE)

    return params["access_token"]
