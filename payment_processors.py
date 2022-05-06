import paypalhttp
from django.conf import settings
from django.utils.module_loading import import_string
from paypalcheckoutsdk.orders import OrdersGetRequest
from rave_python import Rave
from rave_python.rave_exceptions import TransactionVerificationError

from silver.payment_processors import PaymentProcessorBase
from silver.payment_processors.forms import GenericTransactionForm
from silver.payment_processors.mixins import TriggeredProcessorMixin
from .models import FlutterWavePaymentMethod
from .paypal_client import PayPalClient
from .views import FlutterWaveTransactionView
import stripe


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

    
    def refund_transaction(self, transaction, payment_method=None):
        raise NotImplementedError()


    def void_transaction( self, transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def charge_payment(transaction, payment_method=None):
        raise ValueError(transaction)

    def manage_payment( self,transaction, payment_method=None):
        raise NotImplementedError()

    @staticmethod
    def client_token(customer):
        print(customer)

    def handle_transaction_response(self, transaction, request):
        tx_ref = request.GET.get("tx_ref")
        payment_processor = request.GET.get("payment_processor", "flutterwave")
        try:
            if payment_processor == "paypal":
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
            elif payment_processor == "stripe":
                payment_intent = request.GET.get("payment_intent")

                stripe.api_key = settings.STRIPE_SECRET_KEY
                verify_transaction = stripe.PaymentIntent.retrieve(payment_intent)
                payment_status = verify_transaction.status
                if payment_status == "succeeded":
                    verify_transaction["error"] = False
                else:
                    verify_transaction["error"] = payment_status
            else:
                verify_transaction = self.rave.Account.verify(tx_ref)
            transaction_data = {}
            transaction_data.update(transaction.data)
            transaction_data.update(verify_transaction)
            transaction.data = transaction_data
            if verify_transaction["error"] is False:
                transaction.settle()
                try:
                    import_string(settings.SILVER_SUCCESS_TRANSACTION_CALLBACK)(
                        transaction
                    )
                except AttributeError:
                    pass
        except (TransactionVerificationError, paypalhttp.http_error.HttpError) as e:
            if payment_processor == "paypal":
                transaction_data = {"fail_reason": e}
            else:
                transaction_data = {"fail_reason": e.err["errMsg"]}
            transaction_data.update(transaction.data)
            transaction.data = transaction_data
        transaction.save()


class FlutterWaveTriggered(FlutterWaveTriggeredBase):
    @staticmethod
    def is_payment_method_recurring(payment_method):
        return False


class FlutterWaveRecurring(FlutterWaveTriggeredBase):
    @staticmethod
    def is_payment_method_recurring(payment_method):
        return True
