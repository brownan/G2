# -*- coding: utf-8 -*-
import sha
from subprocess import Popen
import os
import signal
import urllib2
import re

from django.conf import settings
MUSIC_PATH = settings.MUSIC_DIR
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
  
def storeSong(path,  info):
  new = open(MUSIC_PATH+'/'+info['sha_hash'] + '.' + info['format'],  'w')
  old = open(path)
  try:
    new.write(old.read())
  finally:
    old.close()
    new.close()
    
def getSong(song):
  return MUSIC_PATH+'/'+ song.sha_hash+ '.' + song.format
  
def start_stream():
  olddir = os.curdir
  os.chdir(settings.LOGIC_DIR)
  #f = open(settings.LOGIC_DIR+"/pid", 'w')
  Popen(["ices", "-c", settings.ICES_CONF]).wait()
  #f.close()
  os.chdir(olddir)
  
def stop_stream():
  Popen(["killall", "-KILL", "ices"]).wait()
  
  
#  
#  d = {}
#  song = MP3(MUSIC_PATH+'/'+sha_hash+'.mp3', ID3=EasyID3)
#  d.update(song)
#  
#  for v in d.keys():
#    d[v] = d[v][0] #1-string list -> string
#
#  d['sha_hash'] = sha_hash
#  d['length'] = round(song.info.length)
#  d['bitrate'] = song.info.bitrate/1000 #b/s -> kb/s
#  
#  if not ("title" in d.keys()):
#    d['title'] = name
#  if 'artist' in d.keys():
#    d['artist'] = self._getObj(d['artist'], Artist)
#  else:
#    d['artist'] = self._getObj("unknown", Artist)
#  if 'album' in d.keys():
#    d['album'] = self._getObj(d['album'], Album)
#  else:
#    d['album'] = self._getObj("unknown", Album)
#    
#  for x in ["tracknumber", "version", "date"]:
#    print x
#    if x in d.keys():
#      print x
#      del d[x]
#  print d.keys()
#    
#  d['uploader'] = self
#  d['format'] = "mp3"

#  print d
#  s = Song(**d)
#
#
#  s.save()
#  self.uploads += 1
#  self.save()
#
def getObj(table, name, oldid=None):
  #get album/artist object if it exists; otherwise create it
  if oldid:
    obj = table.objects.get(id=oldid)
    if obj.songs.count() <= 1:
      obj.songs.clear()
      obj.delete()
  try:
    entry = table.objects.get(name__exact=name)
    entry.name = name
    entry.save()
    return entry
  except table.DoesNotExist:
    t = table(name=name)
    t.save()
    return t


def listenerCount():
  try:
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    s = opener.open(settings.STREAMINFO_URL).read()
  except urllib2.URLError:
    return "?"
  try:
    return listeners.search(s).group(1)
  except (IndexError, AttributeError):
    return "?"
  
  
  