from django import template

register = template.Library()


@register.filter
def getattr(obj, name):

    try:
        value = getattr(obj, name)

        if callable(value):
            return value()

        return value

    except Exception:
        return ""
