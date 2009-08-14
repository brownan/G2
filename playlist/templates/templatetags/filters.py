# -*- coding: utf-8 -*-
from django import template

register = template.Library()

@register.filter
def stom(seconds):
  t = divmod(int(seconds),  60) #get minutes and seconds
  
  if t[1] < 10:
    s = '0' + str(t[1]) #add zero to single digit numbers
  else:
    s = t[1]
  return str(t[0]) + ':' + str(s)
