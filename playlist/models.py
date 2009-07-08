#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from pydj.playlist import utils
import datetime
import shutil

import os
from os.path import basename
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from django.contrib.auth.models import User

class DuplicateError(Exception): pass
class AlreadyOnPlaylistError(Exception): pass
class ScoreOutOfRangeError(Exception): pass

class Artist(models.Model):
  name = models.CharField(max_length=300)
  
  def __unicode__(self): return self.name
  #maybe url, statistics?
  
  class Meta:
    permissions = (
    ("view_artist",  "Can view artist pages."), 
    )


class Album(models.Model):
  name = models.CharField(max_length=300)
  
  def __unicode__(self): return self.name

class Rating(models.Model):
  score = models.FloatField()
  user = models.ForeignKey(User, related_name='ratings', unique=True)
  song = models.ForeignKey('Song', related_name='ratings')
  
  def __unicode__(self): return unicode(self.rating)

  class Meta:
    unique_together = ('user', 'song')

class UserProfile(models.Model):
  user = models.OneToOneField(User,  unique=True)
  uploads = models.IntegerField(default=0)
  
  #settings
  s_playlistHistory = models.IntegerField(default=10, help_text="Number of previously played dongs shown") 
  
  def __unicode__(self): return self.name
  
  def addSong(self,  file):
    
    try: 
      info = self._getSongInfo(file)
      info['sha_hash'] = utils.hashSong(file)
      try:
        Song.objects.get(sha_hash=info['sha_hash'])
      except Song.DoesNotExist: pass
      else:
        raise DuplicateError
      info['uploader'] = self.user
      utils.storeSong(file,  info)
      s = Song(**info)
      s.save()
      self.user.get_profile().uploads += 1
      self.user.save()
        
    finally:
      file.close()
    
  def _getSongInfo(self,  file):
    """Returns dict with tags and stuff"""
    d = {}
    song = MP3(file.temporary_file_path(), ID3=EasyID3)
    d.update(song)
    
    for value in d.keys():
      d[value] = d[value][0] #1-string list -> string
  
    d['length'] = round(song.info.length)
    d['bitrate'] = song.info.bitrate/1000 #b/s -> kb/s
    
    if not ("title" in d.keys()):
      d['title'] = file.name
    if 'artist' in d.keys():
      d['artist'] = Artist.objects.get_or_create(name=d['artist'])[0]
    else:
      d['artist'] = Artist.objects.get_or_create(name="unknown")[0]
    if 'album' in d.keys():
      d['album'] = Album.objects.get_or_create(name=d['album'])[0]
    else:
      d['album'] = Album.objects.get_or_create(name="unknown")[0]
      
    for x in ["tracknumber", "version", "date"]:
      if x in d.keys():
        del d[x]
    print d.keys()
      
    
    d['format'] = "mp3"
    
    return d
    
  #def _getObj(self, name, table):
    #"""get object if it exists; otherwise create it"""
    #try:
      #return table.objects.get(name=name)
    #except:
      #t = table(name=name)
      #t.save()
      #return t
      #def __unicode__(self): return unicode(self.id)
      
  class Meta:
    permissions = (
    ("view_user",  "Can view user pages"), 
    )

  def __unicode__(self): return self.user.name

class Song(models.Model):
  #TODO: sort out artist/composer/lyricist/remixer stuff as per note
  title = models.CharField(max_length=300)
  artist = models.ForeignKey(Artist, blank=True)
  album = models.ForeignKey(Album, blank=True)
  composer = models.CharField(max_length=300, blank=True) #balthcat <3
  lyricist = models.CharField(max_length=300, blank=True)
  remixer = models.CharField(max_length=300, blank=True) #balthcat <3
  genre = models.CharField(max_length=100, blank=True)
  length = models.IntegerField(editable=False) #in seconds
  bitrate = models.IntegerField(editable=False) #in kbps
  sha_hash = models.CharField(max_length=40, unique=True, editable=False)
  add_date = models.DateTimeField(auto_now_add=True, editable=False)
  format = models.CharField(max_length=3, editable=False)
  uploader = models.ForeignKey(User, editable=False)
  category = models.CharField(max_length=20, default="regular")
  
  avgscore = models.FloatField(default=0)
  voteno = models.IntegerField(default=0)
 # ratings = models.ManyToManyField(Rating, null=True, blank=True)
  
  def playlistAdd(self,  user):
    try:
      PlaylistEntry.objects.get(song=self)
    except PlaylistEntry.DoesNotExist: 
      pass
    else:
      raise AlreadyOnPlaylistError
    p = PlaylistEntry(song=self,  adder=user)
    p.save()
  
  def __unicode__(self): return self.artist.name + ' - ' + self.title

  def metadataString(self, user=None):
    #TODO: implement user customisable format strings & typed strings
    if self.category == 'regular':
      return "%s (%s) - %s" % (self.artist, self.album, self.title)
    
  def rate(self, score, user):
    score = int(score)
    if not (0 <= score and score <= 5):
      raise ScoreOutOfRangeError
    
    r = Rating.objects.get_or_create(user=user, song=self)[0]
    r.score = score
    r.save()
    self.avgscore = 0#Rating.objects.get(song=self).aggregate(average=models.Avg('score'))
    #FIXME: install trunk and uncomment that to enable avg scoring & counting
    self.voteno = 0#Rating.objects.get(song=self).count()
    self.save()
    
  
  class Meta:
    permissions = (
    ("view_song",  "Can view song pages"), 
    ("upload_song",  "Can upload songs"), 
    )
    
class PlaylistEntry(models.Model):
  
  song = models.ForeignKey(Song)
  adder = models.ForeignKey(User)
  addtime = models.DateTimeField()
  playtime = models.DateTimeField(null=True, blank=True)
  playing = models.BooleanField(default=False)
  hijack = models.BooleanField(default=False)
  
  def next(self):
    try:
      #set up new entry
      new = PlaylistEntry.objects.get(id__gt=self.id)[0]
      new.playing = True
      new.playtime = datetime.datetime.today()
      #record old one
      old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
      old.save()
      
      self.delete()
      new.save()
      return new
    except PlaylistEntry.DoesNotExist:
      #no more songs :(
      #oh well, repeat this one and record it as having played
      old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
      old.save()
      self.playtime=datetime.datetime.today()
      return self
      
  def save(self):
    if not self.id:
        self.addtime = datetime.datetime.today()
    super(PlaylistEntry, self).save()
    
  def __unicode__(self): return self.song.title
  
  def delSong(self, songid):
    self.entries.objects.get(id=songid).delete()
    self.save()
      
  class Meta:
    ordering = ['hijack', 'id']
    permissions = (
    ("view_playlist",  "Can view the playlist"), 
    ("queue_song",  "Can add song to the playlist"), #golden_appel <3
    ) 
    verbose_name_plural = "Playlist"
    
class OldPlaylistEntry(models.Model):
  song = models.ForeignKey(Song)
  adder = models.ForeignKey(User)
  addtime = models.DateTimeField()
  playtime = models.DateTimeField()
  skipped = models.BooleanField(default=False)
    
  class Meta:
    ordering = ['id']

  
      
    
  





  

