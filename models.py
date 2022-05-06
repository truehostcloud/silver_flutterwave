from silver.models import PaymentMethod




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
