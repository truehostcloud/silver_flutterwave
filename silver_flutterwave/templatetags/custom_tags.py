from django import template
from django.conf import settings
from django.utils.module_loading import import_string

register = template.Library()


class AssignNode(template.Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def render(self, context):
        context[self.name] = getattr(settings, self.value.resolve(context, True), "")
        return ""


@register.tag("get_settings_value")
def do_assign(parser, token):
    bits = token.split_contents()
    if len(bits) != 3:
        raise template.TemplateSyntaxError("'%s' tag takes two arguments" % bits[0])
    value = parser.compile_filter(bits[2])
    return AssignNode(bits[1], value)


@register.simple_tag(takes_context=True)
def convert_user_amount(context, currency, amount):
    """
    Parameters
    ----------
    context: context object
    amount: amount to be converted
    currency: currency of the amount
    Returns
    -------
    converted amount
    """
    customer = context.get("customer")
    if customer:
        currency_converter = import_string(settings.SILVER_CURRENCY_CONVERTER)()
        user_currency = customer.currency
        return round(
            currency_converter.convert(amount, currency, user_currency, None), 2
        )
    return amount


@register.simple_tag(takes_context=True)
def get_user_currency(context, document_currency):
    """
    Parameters
    ----------
    context: context object
    document_currency: currency of the document
    Returns
    -------
    user currency
    """
    customer = context.get("customer")
    if customer:
        return customer.currency
    return document_currency
