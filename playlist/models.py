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
class ScoreOutOfRangeError(Exception): pass
class AddError(Exception): pass

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
    #FIXME: change to uploadSong, ambiguous naming at the moment
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
      if s.length > 60*10: #10 mins
        s.ban("Autobahned because the dong is too long. Ask a mod to unban it if you want to play it.")
      s.save()
      self.user.get_profile().uploads += 1
      self.user.save()
        
    finally:
      file.close()
      
  def addDisallowed(self):
    #check user hasn't got too many songs (currently 3) on the playlist
    if len(PlaylistEntry.objects.filter(adder=self.user)) >= 3:
      return ("you already have too many songs on the playlist", "user is greedy")
    return None
    
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
  
class ChatboxPost(models.Model):
  user = models.ForeignKey(User)
  postdate = models.DateTimeField()
  post = models.CharField(max_length=300)
  

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
  add_date = models.DateTimeField(editable=False)
  format = models.CharField(max_length=3, editable=False)
  uploader = models.ForeignKey(User, editable=False)
  category = models.CharField(max_length=20, default="regular", editable=False)
  
  banned = models.BooleanField(default=False)
  banreason = models.CharField(max_length=100, blank=True)
  unban_adds = models.IntegerField(default=0) #number of plays till rebanned: 0 is forever
  
  avgscore = models.FloatField(default=0)
  voteno = models.IntegerField(default=0)
  # ratings, comments, entries & oldentries are related_names
  
  def addDisallowed(self):
    """Returns (reason, shortreason) tuple. 
    Reason for user, shortreason for add button.
    Otherwise returns None."""
    
    if self.banned:
      return ("song banned", "banned")
    if len(PlaylistEntry.objects.filter(song=self)) > 0:
      return ("song already on playlist", "on playlist")
    #check song hasn't been played recently: dt is definition of 'recently'
    dt = datetime.datetime.now()-datetime.timedelta(days=3)
    if len(OldPlaylistEntry.objects.filter(song=self, playtime__gt=dt)) > 0:
      return ("song played too recently", "recently played")
    return None
    
  def playlistAdd(self,  user):
    """Adds song to the playlist. 
    Raises AddError if there's a problem, with the reason as its only arg."""
    reasons = self.addDisallowed()
    if reasons:
      reason, shortreason = reasons
      raise AddError, reason, shortreason
    reasons = user.get_profile().addDisallowed()
    if reasons:
      reason, shortreason = reasons
      raise AddError, reason, shortreason
    if self.unban_adds:
      self.unban_adds -= 1
      if self.unban_adds == 0:
        self.ban() #assume reason already there
      self.save()
    p = PlaylistEntry(song=self, adder=user)
    if len(PlaylistEntry.objects.filter(playing=True)) == 0:
      p.playing=True
      p.playtime = datetime.datetime.today()
    p.save()
  
  def __unicode__(self): return self.artist.name + ' - ' + self.title
  
  def ban(self, reason=""):
    print "bannned"
    self.banned = True
    if reason:
      self.banreason = reason
    self.save()

  def unban(self, plays=0):
    self.banned = False
    self.unban_adds = plays
    self.save()

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
    
  def comment(self, user, comment):
    c = Comment(text=comment, user=user, song=self)
    c.save()
    print "Commented: %s" % comment
    
    
  def save(self):
    #ensure add_date is creation date
    if not self.id:
        self.add_date = datetime.datetime.today()
    super(Song, self).save()

  class Meta:
    permissions = (
    ("view_song",  "Can view song pages"), 
    ("upload_song",  "Can upload songs"),
    ("ban_song",  "Can ban songs"),
    )
    

    
class Comment(models.Model):
  text = models.CharField(max_length=400)
  user = models.ForeignKey(User, editable=False)
  song = models.ForeignKey(Song, editable=False, related_name="comments")
  time = models.IntegerField(default=0)
  datetime = models.DateTimeField()
  
  def save(self):
    #ensure datetime is creation date
    if not self.id:
        self.datetime = datetime.datetime.today()
    super(Comment, self).save()
    
class PlaylistEntry(models.Model):
  
  song = models.ForeignKey(Song, related_name="entries")
  adder = models.ForeignKey(User)
  addtime = models.DateTimeField()
  playtime = models.DateTimeField(null=True, blank=True)
  playing = models.BooleanField(default=False)
  hijack = models.BooleanField(default=False)
  
  def next(self):
    try:
      #set up new entry
      new = PlaylistEntry.objects.filter(id__gt=self.id)[0]
    except PlaylistEntry.DoesNotExist:
      #no more songs :(
      #oh well, repeat this one and record it as having played
      old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
      old.save()
      self.playtime=datetime.datetime.today()
      return self
      
    new.playing = True
    new.playtime = datetime.datetime.today()
    #record old one
    old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
    old.save()
    
    self.delete()
    new.save()
    return new

      
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
  song = models.ForeignKey(Song, related_name="oldentries")
  adder = models.ForeignKey(User)
  addtime = models.DateTimeField()
  playtime = models.DateTimeField()
  skipped = models.BooleanField(default=False)
    
  class Meta:
    ordering = ['id']

  
      
    
  





  

