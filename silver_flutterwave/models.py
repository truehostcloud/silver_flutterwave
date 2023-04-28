import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from silver.models import PaymentMethod, Customer as BaseCustomer
from django_countries.fields import CountryField


class FlutterWavePaymentMethod(PaymentMethod):
    class Meta:
        proxy = True

    class Types:
        PayPal = "paypal_account"
        CreditCard = "credit_card"

    @property
    def token(self):
        return self.decrypt_data(self.data.get("token"))

    @token.setter
    def token(self, value):
        self.data["token"] = self.encrypt_data(value)

    @property
    def nonce(self):
        return self.decrypt_data(self.data.get("nonce"))

    @nonce.setter
    def nonce(self, value):
        self.data["nonce"] = self.encrypt_data(value)

    def update_details(self, details):
        if "details" not in self.data:
            self.data["details"] = details
        else:
            self.data["details"].update(details)

    @property
    def details(self):
        return self.data.get("details")

    @property
    def public_data(self):
        return self.data.get("details")


class CurrencyConversion(models.Model):
    """
    Model to store currency conversions fetched from remote converter.
    Used to reduce calls to remote or as a fallback in case of unavailability of remote.
    """

    from_currency_code = models.CharField(max_length=4, null=True, blank=True)
    to_currency_code = models.CharField(max_length=4, null=True, blank=True)
    rate = models.FloatField(null=True, blank=True)
    rate_date = models.DateTimeField(auto_now_add=True)


class Customer(BaseCustomer):
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)

    def get_stripe_customer_id(self):
        """Get the stripe customer id for this customer"""
        if not self.stripe_customer_id:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            customer = stripe.Customer.create(
                email=self.email,
                name=self.name,
                description=self.name,
            )
            self.stripe_customer_id = customer.id
            self.save()
        return self.stripe_customer_id

    def add_stripe_card(self, token, name):
        """
        Add a card to a customer's account
        :param token:
        :param name:
        :return:
        """
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe_customer_id = self.get_stripe_customer_id()
        try:
            stripe.Customer.create_source(
                stripe_customer_id, source=token, metadata={"name": name}
            )
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get("error", {})
            raise ValidationError(err.get("message"))
        card = stripe.Token.retrieve(token).card
        return card

    def delete_stripe_card(self, card_id):
        """
        Delete a card from a customer's account
        :param card_id:
        :return:
        """
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe_customer_id = self.get_stripe_customer_id()
        stripe.Customer.delete_source(stripe_customer_id, card_id)

    def card_exists(self, token):
        """
        Check if a customer has a card with the given fingerprint
        :param token:
        :return:
        """
        stripe.api_key = settings.STRIPE_SECRET_KEY
        card = stripe.Token.retrieve(token).card
        return self.cards.filter(fingerprint=card.fingerprint).exists()


class Card(models.Model):
    """Model to store card details fetched from remote."""

    BRAND_CHOICES = (
        ("visa", "Visa"),
        ("mastercard", "MasterCard"),
        ("dinersclub", "Diners Club"),
        ("discover", "Discover"),
        ("jcb", "JCB"),
        ("unionpay", "UnionPay"),
        ("americanexpress", "American Express"),
        ("eftposaustralia", "Eftpos Australia"),
        ("unknown", "Unknown"),
    )
    FUNDING_CHOICES = (
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("prepaid", "Prepaid"),
        ("unknown", "Unknown"),
    )
    CVC_CHECK_CHOICES = (
        ("pass", "Pass"),
        ("fail", "Fail"),
        ("unavailable", "Unavailable"),
        ("unchecked", "Unchecked"),
    )
    display_name = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    fingerprint = models.CharField(max_length=255, null=True, blank=True)
    external_name = models.CharField(max_length=255, null=True, blank=True)
    brand = models.CharField(
        max_length=255, null=True, blank=True, choices=BRAND_CHOICES
    )
    last4 = models.CharField(max_length=4, null=True, blank=True)
    exp_month = models.CharField(max_length=2, null=True, blank=True)
    exp_year = models.CharField(max_length=4, null=True, blank=True)
    address_zip = models.CharField(max_length=255, null=True, blank=True)
    address_city = models.CharField(max_length=255, null=True, blank=True)
    address_state = models.CharField(max_length=255, null=True, blank=True)
    address_country = models.CharField(max_length=255, null=True, blank=True)
    cvc_check = models.CharField(
        max_length=255, null=True, blank=True, choices=CVC_CHECK_CHOICES
    )
    address_line1_check = models.CharField(max_length=255, null=True, blank=True)
    address_zip_check = models.CharField(max_length=255, null=True, blank=True)
    funding = models.CharField(
        max_length=255, null=True, blank=True, choices=FUNDING_CHOICES
    )
    metadata = models.JSONField(null=True, blank=True)
    country = CountryField(null=True, blank=True)
    payment_method = models.ForeignKey(
        FlutterWavePaymentMethod, on_delete=models.CASCADE, related_name="cards"
    )
    added_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="cards", null=True, blank=True
    )
    default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.display_name} {self.brand} {self.last4}"

    def delete(self, using=None, keep_parents=False):
        if self.customer:
            if self.default:
                customer_cards = self.customer.cards.all()
                if customer_cards.count() > 1:
                    new_default = customer_cards.exclude(id=self.id).first()
                    new_default.default = True
                    new_default.save()
            self.customer.delete_stripe_card(self.external_id)
        super().delete(using=using, keep_parents=keep_parents)
