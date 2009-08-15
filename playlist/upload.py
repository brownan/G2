# -*- coding: utf-8 -*-
import os.path
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import hashlib
from django.core.management import setup_environ
from pydj import settings
setup_environ(settings)
from pydj.playlist.models import *
from django.contrib.auth.models import User

class UnsupportedFormatError(Exception): pass
class CorruptFileError(Exception): pass

class UploadedFile:
  supported_types = ['mp3'] #TODO: ogg (and m4a?)
  def __init__(self, file, realname=None, filetype=None):
    
    self.type = filetype
    
    if realname is None:
      realname = os.path.basename(file)
    self.realname = realname
    
    if self.type is None:
      self.type = os.path.splitext(realname)[1].strip('.')
      
    self.type = self.type.lower()  
    
    if self.type not in self.supported_types:
      raise UnsupportedFormatError, "%s not supported" % self.type
    
    self.info = {}
    self.file = file
    self.getHash()
    self.getTags()
    
    
    
  def getHash(self):
    """Populates self.sha_hash with sha1 hash of uploaded file."""
    f = open(self.file)
    self.info['sha_hash'] = hashlib.sha1(f.read()).hexdigest()
    f.close()
  
  def getTags(self):
    """Run correct tagging method. 
    
    Method name format: get<type in uppercase>Tags"""
    getattr(self, 'get'+self.type.upper()+'Tags')()
    
  def getMP3Tags(self):
    """Returns dict with tags and stuff"""
    tags = {}
    
    try:
      song = MP3(self.file, ID3=EasyID3)
    except mutagen.mp3.HeaderNotFoundError:
      raise CorruptFileError
    
    tags.update(song)
    
    for value in tags.keys():
      tags[value] = tags[value][0] #list to string (first element)
  
    tags['length'] = round(song.info.length)
    tags['bitrate'] = song.info.bitrate/1000 #b/s -> kb/s
    if not ("title" in tags.keys()):
      tags['title'] = self.realname
    if 'artist' in tags.keys():
      tags['artist'] = Artist.objects.get_or_create(name=tags['artist'])[0]
    else:
      tags['artist'] = Artist.objects.get_or_create(name='(unknown)')[0]
    if 'album' in tags.keys():
      tags['album'] = Album.objects.get_or_create(name=tags['album'])[0]
    else: 
      tags['album'] = Album.objects.get_or_create(name='(empty)')[0]
    
    for x in ["tracknumber", "version", "date"]:
      if x in tags.keys():
        del tags[x] #not stored
    tags['format'] = "mp3"
    
    self.info.update(tags)

#if __name__ == "__main__":
  #u = UploadedFile("/home/jadh/mus/Collection/06 - Weight Of My Words.mp3")
  #print u.info
  #User.objects.get(username='jj').get_profile().uploadSong(u)
    
    