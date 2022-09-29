import stripe
from django.conf import settings
from money.currency import Currency
from money.money import Money

from silver.payment_processors import get_instance
from silver.payment_processors.views import GenericTransactionView


class FlutterWaveTransactionView(GenericTransactionView):
    @staticmethod
    def get_stripe_client_secret(transaction):
        """Get the Stripe client secret for the transaction."""
        _ = "https://api.stripe.com/v1/payment_intents"
        amount = transaction.invoice.total
        currency = transaction.invoice.currency
        smallest_amount_unit = Money(amount, getattr(Currency, currency)).sub_units
        payload = {
            "amount": smallest_amount_unit,
            "currency": currency,
            "automatic_payment_methods[enabled]": True,
        }
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent_response = stripe.PaymentIntent.create(**payload)
        return intent_response.get("client_secret")

    def get_context_data(self):
        context_data = super(FlutterWaveTransactionView, self).get_context_data()
        payment_processor = get_instance(self.transaction.payment_processor)
        context_data["client_token"] = payment_processor.client_token(
            self.transaction.customer
        )
        context_data["is_recurring"] = payment_processor.is_payment_method_recurring(
            self.transaction.payment_method
        )

        context_data["client_secret"] = self.get_stripe_client_secret(self.transaction)
        return context_data
