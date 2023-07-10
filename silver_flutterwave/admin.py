from django.contrib import admin
from .models import CurrencyConversion, Card


class CurrencyConversionAdmin(admin.ModelAdmin):
    list_display = ("from_currency_code", "to_currency_code", "rate", "rate_date")


class CardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "brand",
        "last4",
        "exp_month",
        "exp_year",
        "country",
        "customer",
        "active",
        "decline_code",
    )


admin.site.register(CurrencyConversion, CurrencyConversionAdmin)
admin.site.register(Card, CardAdmin)
