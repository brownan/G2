#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

from pyquery import PyQuery as pq
from urllib import urlretrieve

import settings
from django.core.management import setup_environ
setup_environ(settings)
from django.conf import settings
from playlist.models import Emoticon

EMOTICONS_URL = settings.EMOTICONS_URL 
EMOTICONS_STORAGE = os.path.join(settings.IMAGES_DIR, "emoticons")

p = pq(url=EMOTICONS_URL)
ul = p("li.smilie")

def get_emoticon(url):
  """Download an emoticon from a URL, save it, and return the filename"""
  global EMOTICONS_STORAGE
  filename = os.path.basename(url)
  print "getting %s..." % (filename)
  urlretrieve(url, os.path.join(EMOTICONS_STORAGE, filename))
  return filename
  

if Emoticon.objects.all().count() == 0:
  #first run
  for li in ul:
    Emoticon(
      text=pq(li).children("div.text").html(), 
      alt_text=pq(li).children("img").attr("title"), 
      filename=get_emoticon(pq(li).children("img").attr("src"))
    ).save()

else:
  for li in ul:
    try:
      Emoticon.objects.get(text=pq(li).children("div.text").html())
    except Emoticon.DoesNotExist:
      Emoticon(
        text=pq(li).children("div.text").html(), 
        alt_text=pq(li).children("img").attr("title"), 
        filname=get_emoticon(pq(li).children("img").attr("src"))
      ).save()