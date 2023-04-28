from silver.payment_processors import get_instance
from silver.payment_processors.views import GenericTransactionView


class FlutterWaveTransactionView(GenericTransactionView):
    def get_context_data(self):
        """Add the client token to the context data."""
        context_data = super(FlutterWaveTransactionView, self).get_context_data()
        payment_processor = get_instance(self.transaction.payment_processor)
        context_data["client_token"] = payment_processor.client_token(
            self.transaction.customer
        )
        context_data["is_recurring"] = payment_processor.is_payment_method_recurring(
            self.transaction.payment_method
        )
        stripe_payment_intent = payment_processor.create_stripe_payment_intent(
            self.transaction, self.request
        )
        context_data["client_secret"] = stripe_payment_intent.get("client_secret")
        return context_data
