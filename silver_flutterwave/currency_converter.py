import json
from datetime import datetime, timedelta

import requests
from _decimal import Decimal
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.timezone import make_aware


class RateNotFound(Exception):
    """
    Exception raised when a rate is not found.
    """

    def __init__(self, from_currency=None, to_currency=None, date=None):
        """
        Initialize the exception.
        :param from_currency:
        :param to_currency:
        :param date:
        """
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.date = date

    def __str__(self):
        if not all([self.from_currency, self.to_currency]):
            return "No rate was found."

        if not self.date:
            return "No rate for {} to {}.".format(self.from_currency, self.to_currency)

        return "No rate for {} to {}, from {} was found.".format(
            self.from_currency, self.to_currency, self.date
        )


class CurrencyConverter:
    """
    A class to convert one currency to another.
    ...
    Methods
    -------
    save_conversion(from_currency, to_currency, rate):
        Save the conversion rate into the database.
    get_saved_conversion(from_currency, to_currency):
        Get saved conversion rate from the database.
    fetch_rate_from_converter(api_key, query):
        Get saved conversion rate from remote converter.
    convert(cls, amount, from_currency, to_currency, date):
        Convert one currency to another.
    """

    @staticmethod
    def save_conversion(from_currency, to_currency, rate):
        """
        Save the conversion rate into the database.
        Args:
          from_currency: String, currency code converting from.
          to_currency: String, currency code converting to.
          rate: Decimal, currency conversion rate date.
        """
        currency_conversion = import_string(settings.SILVER_CURRENCY_CONVERSION_MODEL)
        currency_conversion.objects.create(
            from_currency_code=from_currency,
            to_currency_code=to_currency,
            rate=rate,
        )

    @classmethod
    def get_saved_conversion(cls, from_currency, to_currency, datetime_gte=None):
        """
        Get saved conversion rate from the database.
        Args:
          from_currency: String, currency code converting from.
          to_currency: String, currency code converting to.
          datetime_gte: datetime to start from
        Returns:
            Decimal, Conversion rate
        """
        currency_conversion = import_string(settings.SILVER_CURRENCY_CONVERSION_MODEL)
        if from_currency == to_currency:
            return 1
        rate_filter = currency_conversion.objects.filter(
            from_currency_code=from_currency, to_currency_code=to_currency
        )
        if datetime_gte:
            rate_object = rate_filter.filter(rate_date__gte=datetime_gte).last()
        else:
            rate_object = rate_filter.last()
        if rate_object:
            return rate_object.rate
        raise RateNotFound(from_currency=from_currency, to_currency=to_currency)

    @staticmethod
    def fetch_rate_from_converter(api_key, query):
        """
        Get saved conversion rate from remote converter.
        Args:
          api_key: String, currency code converting from.
          query: String, conversion rate query string e.g. USD_KES.
        Returns:
            Integer, Conversion rate
        """
        get_params = "compact=ultra&apiKey={}&q={}".format(api_key, query)
        url = "https://free.currconv.com/api/v7/convert?" + get_params
        response = requests.request("GET", url)
        try:
            rate = json.loads(response.text.encode("utf8"))
            return rate[query]
        except (json.decoder.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def fallback_rate_from_converter(api_key, from_currency, to_currency):
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"
        response = requests.request("GET", url)
        try:
            rate = json.loads(response.text.encode("utf8"))
            return rate["conversion_rate"]
        except (json.decoder.JSONDecodeError, KeyError):
            return None

    @classmethod
    def convert(cls, amount, from_currency, to_currency, conversion_date):
        """
        Convert one currency to another.
        Args:
          amount: Integer amount to be converted.
          from_currency: String, currency code converting from.
          to_currency: String, currency code converting to.
          conversion_date: String, currency conversion rate date.
        Returns:
          Decimal, converted amount or conversion rate.
        """
        currency_converter_api_key = settings.CURRENCY_CONVERTER_API_KEY
        exchange_rate_api_key = settings.EXCHANGE_RATE_API_KEY

        query = "{}_{}".format(from_currency, to_currency)
        _24_hours_ago = make_aware(datetime.now() - timedelta(hours=24))
        if settings.FIXED_CURRENCY_CONVERSIONS.get(query):
            rate = settings.FIXED_CURRENCY_CONVERSIONS[query]
        else:
            try:
                rate = cls.get_saved_conversion(
                    from_currency, to_currency, datetime_gte=_24_hours_ago
                )
            except RateNotFound:
                rate = cls.fetch_rate_from_converter(currency_converter_api_key, query)
                if not rate:
                    rate = cls.fallback_rate_from_converter(exchange_rate_api_key, from_currency, to_currency)
                if rate:
                    cls.save_conversion(from_currency, to_currency, rate)
                else:
                    rate = cls.get_saved_conversion(from_currency, to_currency)
        if type(amount) is Decimal:
            return Decimal(rate) * amount
        return Decimal(rate * amount)
