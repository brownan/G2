# -*- coding: utf-8 -*-
import sha
from subprocess import Popen
import os
import signal
import urllib2
import re

from django.conf import settings
GHETTO_URL = "http://ghettoradio.us:8209/"
listeners =  re.compile(r'(\d+) of \d+ listeners \(\d+ unique\)')

def hashSong(file):
  """Returns sha5 hash of uploaded file. Assumes file is safely closed outside"""
  sha_hash = sha.new("")
  if file.multiple_chunks():
    for chunk in file.chunks():
      sha_hash.update(chunk)
  else:
    sha_hash.update(file.read())
  return sha_hash.hexdigest()  
  
    
def getSong(song):
  return song.getPath()
  
def start_stream():
  olddir = os.curdir
  os.chdir(settings.LOGIC_DIR)
  #f = open(settings.LOGIC_DIR+"/pid", 'w')
  Popen(["ices", "-c", settings.ICES_CONF],
          close_fds=True).wait()
  #f.close()
  os.chdir(olddir)
  
def stop_stream():
  Popen(["killall", "-KILL", "ices"]).wait()
  
def getObj(table, name, oldid=None):
  #get album/artist object if it exists; otherwise create it
  try:
    entry = table.objects.get(name__exact=name)
    entry.name = name
    entry.save()
    return entry
  except table.DoesNotExist:
    t = table(name=name)
    t.save()
    return t


def listenerCount(url):
  try:
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    s = opener.open(url).read()
  except urllib2.URLError:
    return "?"
  try:
    return listeners.search(s).group(1)
  except (IndexError, AttributeError):
    return "?"
    
def ghettoListenerCount():
  return listenerCount(GHETTO_URL)
  
def gbsfmListenerCount():
  return listenerCount(settings.STREAMINFO_URL)
    
    
    
  
  
  
