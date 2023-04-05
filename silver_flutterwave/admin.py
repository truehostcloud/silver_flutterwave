from django.contrib import admin
from .models import CurrencyConversion


class CurrencyConversionAdmin(admin.ModelAdmin):
    list_display = ("from_currency_code", "to_currency_code", "rate", "rate_date")


admin.site.register(CurrencyConversion, CurrencyConversionAdmin)
