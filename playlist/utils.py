# -*- coding: utf-8 -*-
import sha
from django.conf import settings

MUSIC_PATH = settings.MUSIC_DIR

def hashSong(file):
  """Returns sha5 hash of uploaded file. Assumes file is safely closed outside"""
  sha_hash = sha.new("")
  if file.multiple_chunks():
    for chunk in file.chunks():
      sha_hash.update(chunk)
  else:
    sha_hash.update(file.read())
  return sha_hash.hexdigest()  
  
def storeSong(file,  info):
  f = open(MUSIC_PATH+'/'+info['sha_hash'] + '.' + info['format'],  'w')
  try:
    if file.multiple_chunks():
      for chunk in file.chunks():
        f.write(chunk)
    else:
      f.write(file.read())
  finally:
    f.close()
    
def getSong(song):
  return MUSIC_PATH+'/'+ song.sha_hash+ '.' + song.format
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
#def _getObj(self, name, table):
#  #get object if it exists; otherwise create it
#  try:
#    return table.objects.get(name=name)
#  except:
#    t = table(name=name)
#    t.save()
#    return t
