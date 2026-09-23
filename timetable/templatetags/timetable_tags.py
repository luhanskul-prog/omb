
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except Exception:
        return None


@register.filter
def getattr(obj, name):
    if obj is None:
        return ""

    try:
        value = getattr(obj, name)
    except Exception:
        return ""

    if callable(value):
        try:
            return value()
        except Exception:
            return ""

    return value
