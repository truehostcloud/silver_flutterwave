from django.db import models

from silver.models import PaymentMethod, Customer
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

    def __str__(self):
        return f"{self.display_name} {self.brand} {self.last4}"

    def delete(self, using=None, keep_parents=False):
        if self.customer:
            users = self.customer.users.all()
            if users:
                users.filter(
                    stripe_customer_id__isnull=False
                ).first().delete_stripe_card(self.external_id)
        super().delete(using=using, keep_parents=keep_parents)
