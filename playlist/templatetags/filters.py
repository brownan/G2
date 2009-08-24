# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe

register = template.Library()

register = template.Library()

@register.filter
def stom(seconds):
  t = divmod(int(seconds),  60) #get minutes and seconds
  
  if t[1] < 10:
    s = '0' + str(t[1]) #add zero to single digit numbers
  else:
    s = t[1]
  return str(t[0]) + ':' + str(s)


@register.filter
def bbcode(value):
    """
    Generates (X)HTML from string with BBCode "markup".
    By using the postmark lib from:
    @see: http://code.google.com/p/postmarkup/
    
    """ 
    try:
        from postmarkup import render_bbcode
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% bbcode %} filter: The Python postmarkup library isn't installed."
        return force_unicode(value)
    else:
        return mark_safe(render_bbcode(value))
bbcode.is_save = True

@register.filter
def strip_bbcode(value):
    """ 
    Strips BBCode tags from a string
    By using the postmark lib from: 
    @see: http://code.google.com/p/postmarkup/
    
    """ 
    try:
        from postmarkup import strip_bbcode
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% bbcode %} filter: The Python postmarkup library isn't installed."
        return force_unicode(value)
    else:
        return mark_safe(strip_bbcode(value))
bbcode.is_save = True
