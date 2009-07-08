# -*- coding: utf-8 -*-
import urllib
NEXT_URL="http://localhost:8000/next/777"


def ices_init():
  pass

def ices_get_next():

  l = urllib.urlopen(NEXT_URL).readlines()
  global l
  return l[0][:-1]

def ices_get_metadata():
  global l
  return l[1]
