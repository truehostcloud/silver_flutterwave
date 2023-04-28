import requests
import paypalhttp
from django.conf import settings
from django.utils.module_loading import import_string
from money.currency import Currency
from money.money import Money
from paypalcheckoutsdk.orders import OrdersGetRequest
from rave_python import Rave
from rave_python.rave_exceptions import TransactionVerificationError

from silver.payment_processors import PaymentProcessorBase
from silver.payment_processors.forms import GenericTransactionForm
from silver.payment_processors.mixins import TriggeredProcessorMixin
from silver.utils.payments import get_payment_complete_url
from .models import FlutterWavePaymentMethod
from .paypal_client import PayPalClient
from .views import FlutterWaveTransactionView
import stripe
from silver.models import Transaction


class FlutterWaveTriggeredBase(PaymentProcessorBase, TriggeredProcessorMixin):
    payment_method_class = FlutterWavePaymentMethod
    transaction_view_class = FlutterWaveTransactionView
    form_class = GenericTransactionForm
    template_slug = "flutterwave"
    if settings.DEBUG:
        rave = Rave(
            settings.FLUTTERWAVE_PUBLIC_KEY,
            settings.FLUTTERWAVE_SECRET_KEY,
            usingEnv=False,
        )
    else:
        rave = Rave(
            settings.FLUTTERWAVE_PUBLIC_KEY,
            settings.FLUTTERWAVE_SECRET_KEY,
            production=True,
        )

    _has_been_setup = False

    def __init__(self, name, *args, **kwargs):
        super(FlutterWaveTriggeredBase, self).__init__(name)

        if self._has_been_setup:
            return

        FlutterWaveTriggeredBase._has_been_setup = True

    @staticmethod
    def refund_transaction(transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def void_transaction(transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def charge_payment(transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def manage_payment(transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def client_token(customer):
        return customer.id

    @staticmethod
    def settle_transaction(transaction):
        """Settle the transaction and call the success callback if it exists."""
        transaction.settle()
        try:
            import_string(settings.SILVER_SUCCESS_TRANSACTION_CALLBACK)(transaction)
        except AttributeError:
            pass
        transaction.save()
        return transaction

    @staticmethod
    def build_stripe_payment_intent_payload(transaction, request):
        """Build the payload for the Stripe Payment Intent API call."""
        amount = transaction.invoice.total
        currency = transaction.invoice.currency
        customer = transaction.customer
        extended_customer = customer.customer
        smallest_amount_unit = Money(amount, getattr(Currency, currency)).sub_units
        payload = {
            "amount": smallest_amount_unit,
            "currency": currency,
            "automatic_payment_methods[enabled]": True,
        }
        if extended_customer.stripe_customer_id:
            payload["customer"] = extended_customer.stripe_customer_id
            customer_card = extended_customer.cards.filter(default=True).first()
            if customer_card:
                payload["payment_method"] = customer_card.external_id
                payload["off_session"] = True
                payload["confirm"] = True
                return_url = f"{get_payment_complete_url(transaction, request)}?payment_processor=stripe"
                if request is None:
                    return_url = f"{settings.SILVER_DEFAULT_BASE_URL}{return_url}"
                payload["return_url"] = return_url
        return payload

    def create_stripe_payment_intent(self, transaction, request):
        payload = self.build_stripe_payment_intent_payload(transaction, request)
        transaction_data = transaction.data or {}
        if transaction_data.get("id") and transaction_data.get("client_secret"):
            return transaction_data
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            intent_response = stripe.PaymentIntent.create(**payload)
            transaction_data = {}
            transaction_data.update(transaction.data)
            transaction_data.update(intent_response)
            transaction.data = transaction_data
            transaction.save()
            if (
                intent_response.status == "succeeded"
                and intent_response.amount == intent_response.amount_received
            ):
                self.settle_transaction(transaction)
            return intent_response
        except stripe.error.InvalidRequestError as e:
            transaction_data = {}
            transaction_data.update(transaction.data)
            transaction_data.update(e.json_body)
            transaction.data = transaction_data
            transaction.save()
            return e

    @staticmethod
    def handle_paypal_response(_transaction, request):
        order_id = request.GET.get("order_id")
        request = OrdersGetRequest(order_id)
        paypal_client = PayPalClient()
        order_response = paypal_client.client.execute(request)
        order_status = order_response.result.status
        order_error = True
        if order_status == "COMPLETED":
            order_error = False
        verify_transaction = {
            "status_code": order_response.status_code,
            "status": order_status,
            "order_id": order_response.result.id,
            "intent": order_response.result.intent,
            "error": order_error,
        }
        return verify_transaction

    @staticmethod
    def handle_stripe_response(transaction, request):
        payment_intent = request.GET.get("payment_intent")
        if payment_intent in [None, ""]:
            transaction_data = transaction.data
            payment_intent = transaction_data.get("id")
        payment_intent_client_secret = request.GET.get("STRIPE_PUBLISHABLE_KEY")

        stripe.api_key = settings.STRIPE_SECRET_KEY

        verify_transaction = stripe.PaymentIntent.retrieve(
            payment_intent, payment_intent_client_secret
        )
        payment_status = verify_transaction.status
        if payment_status == "succeeded":
            verify_transaction["error"] = False
        else:
            verify_transaction["error"] = payment_status
        return verify_transaction

    @staticmethod
    def handle_mpesa_response(transaction, request):
        business_no = request.GET.get("business_no")
        transaction_code = request.GET.get("transaction_code")
        base_url = "https://my.jisort.com"
        api_path = "/general_ledger/transactions_ledger/"
        url = f"{base_url}{api_path}"
        response = requests.get(
            f"{url}?business_no={business_no}&trans_id={transaction_code}"
        )
        verify_transaction = {}
        if response.status_code != 200:
            error = response.json()
            verify_transaction["error"] = error[0]
        else:
            mpesa_transaction_details = response.json()
            if float(mpesa_transaction_details["debit"]) < transaction.amount:
                verify_transaction[
                    "error"
                ] = "Transaction amount is less than amount invoiced"
            else:
                verify_transaction = mpesa_transaction_details
                verify_transaction["error"] = False
        return verify_transaction

    def handle_flutterwave_response(self, _transaction, request):
        tx_ref = request.GET.get("tx_ref")
        verify_transaction = self.rave.Account.verify(tx_ref)
        return verify_transaction

    def handle_transaction_response(self, transaction, request):
        payment_processor = request.GET.get("payment_processor", "flutterwave")
        try:
            handler = getattr(self, f"handle_{payment_processor}_response")
            verify_transaction = handler(transaction, request)
            transaction_data = {}
            transaction_data.update(transaction.data)
            transaction_data.update(verify_transaction)
            transaction.data = transaction_data
            if verify_transaction["error"] is False:
                self.settle_transaction(transaction)
        except (TransactionVerificationError, paypalhttp.http_error.HttpError) as e:
            if payment_processor == "paypal":
                transaction_data = {"fail_reason": e}
            else:
                transaction_data = {"fail_reason": e.err["errMsg"]}
            transaction_data.update(transaction.data)
            transaction.data = transaction_data
        transaction.save()

    def execute_transaction(self, transaction):
        self.create_stripe_payment_intent(transaction, None)

    def fetch_transaction_status(self, transaction):
        transaction_data = transaction.data or {}
        if transaction_data.get("id") and transaction_data.get("client_secret"):
            payment_intent_id = transaction_data.get("id")
            stripe.api_key = settings.STRIPE_SECRET_KEY
            payment_intent = stripe.PaymentIntent.retrieve(
                payment_intent_id, expand=["latest_charge"]
            )
            transaction_data = {}
            transaction_data.update(transaction.data)
            transaction_data.update(payment_intent)
            transaction.data = transaction_data
            refunded = payment_intent.latest_charge.refunded
            if (
                payment_intent.status == "succeeded"
                and payment_intent.amount == payment_intent.amount_received
                and transaction.state
                in [Transaction.States.Pending, Transaction.States.Initial]
            ):
                transaction = self.settle_transaction(transaction)
            if refunded and transaction.state == Transaction.States.Settled:
                refunds = stripe.Refund.list(charge=payment_intent.latest_charge.id)
                refund_reason = None
                for refund in refunds:
                    refund_reason = refund.reason
                    break
                transaction.refund(
                    refund_code=refund_reason,
                )
            transaction.save()


class FlutterWaveTriggered(FlutterWaveTriggeredBase):
    @staticmethod
    def is_payment_method_recurring(payment_method):
        return False


class FlutterWaveRecurring(FlutterWaveTriggeredBase):
    @staticmethod
    def is_payment_method_recurring(payment_method):
        return True
