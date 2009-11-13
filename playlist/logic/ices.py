# -*- coding: utf-8 -*-
import urllib
import os
import sys
sys.path.append("/home/jonnty/")
import pydj.settings

NEXT_URL="http://localhost/next/"+pydj.settings.NEXT_PASSWORD


def ices_init():
  f = open("pid", "w")
  f.write(str(os.getpid()))
  f.close()
  

def ices_get_next():

  l = urllib.urlopen(NEXT_URL).readlines()
  global l
  return l[0][:-1]

def ices_get_metadata():
  global l
  return l[1]
