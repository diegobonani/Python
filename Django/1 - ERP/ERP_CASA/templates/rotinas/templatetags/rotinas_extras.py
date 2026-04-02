from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None