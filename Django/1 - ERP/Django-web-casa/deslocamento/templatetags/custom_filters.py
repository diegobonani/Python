# deslocamento/templatetags/custom_filters.py

from django import template
import json

# IMPORTANTE: A variável de registro DEVE ser chamada 'register'
register = template.Library()

@register.filter(name='from_json')
def from_json(value):
    """
    Converte uma string JSON em um objeto Python.
    """
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None