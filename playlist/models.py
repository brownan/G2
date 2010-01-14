#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models
from pydj.playlist import utils
from subprocess import Popen
import datetime
import shutil
import os
from os.path import basename
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from django.contrib.auth.models import User
#import pydj.dbsettings as dbsettings
from django.db import IntegrityError 
from django.conf import settings
from django.db.models.signals import pre_save
from django.db.models import Avg, Count, Sum
from django.db.models.query import QuerySet
from playlist.cue import CueFile


MUSIC_PATH = settings.MUSIC_DIR

class DuplicateError(Exception): pass
class ScoreOutOfRangeError(Exception): pass
class AddError(Exception): pass
class FileTooBigError(Exception): pass



class Artist(models.Model):
  name = models.CharField(max_length=255, unique=True)
  sort_name = models.CharField(max_length=300)
  
  def __unicode__(self): return self.name
  #maybe url, statistics?
  
  class Meta:
    permissions = (
    ("view_artist",  "g2 Can view artist pages."), 
    )
  #def save(self):
    ##clean up name and change sort_name
    #self.name = self.name.strip()
    #if len(self.name) > 4:
      #self.sort_name = self.name[:4].lower()=="the " and self.name[4:] or self.name
    #else:
      #self.sort_name = self.name
    #self.sort_name = self.sort_name.lstrip("'\"")
    
    #super(Artist, self).save()
    
def artist_handler(sender, **kwargs):
  instance = kwargs['instance']
  #clean up name and change sort_name
  instance.name = instance.name.strip()
  instance.sort_name = instance.name.lstrip("'\"")
  if len(instance.name) > 4:
    instance.sort_name = instance.sort_name[:4].lower()=="the " and instance.sort_name[4:] or instance.sort_name
  else:
    instance.sort_name = instance.sort_name
  
def dupe_handler(sender, **kwargs):
  instance = kwargs['instance']
  for dupe in sender.objects.filter(name=instance.name):
    for song in dupe.songs.all():
      instance.songs.add(song)
    dupe.delete()


pre_save.connect(artist_handler, sender=Artist)
#pre_save.connect(dupe_handler, sender=Artist)

class Album(models.Model):
  name = models.CharField(max_length=255, unique=True)
  
  def __unicode__(self): return self.name

class Rating(models.Model):
  score = models.FloatField()
  user = models.ForeignKey(User, related_name='ratings')
  song = models.ForeignKey('Song', related_name='ratings')
  
  def __unicode__(self): return unicode(self.score)

  class Meta:
    unique_together = ('user', 'song')
    permissions = (
    ("can_rate",  "g2 Can rate songs"), 
    )

class UserProfile(models.Model):
  user = models.OneToOneField(User,  unique=True)
  uploads = models.IntegerField(default=0)
  #last_ip = models.CharField(max_length=15)
  api_key = models.CharField(max_length=40, editable=False, blank=True)
  sa_id = models.IntegerField(blank=True, null=True, unique=True,
                              help_text="Something Awful account ID") 
  
  #settings
  s_playlistHistory = models.IntegerField(default=10, help_text="Number of previously played dongs shown") 
  
  def __unicode__(self): return self.name
  
  def addSong(self,  file):
    #FIXME: change to uploadSong, ambiguous naming at the moment (fixed)
    #DEPRECIATED
    try: 
      info = self._getSongInfo(file)
      info['sha_hash'] = utils.hashSong(file)
      try:
        Song.objects.get(sha_hash=info['sha_hash'])
      except Song.DoesNotExist: pass
      else:
        raise DuplicateError
      if file.size > 50000000: #SETTING
        raise FileTooBigError
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
  
  def uploadSong(self, upload):
    """Add an UploadedSong to the database if allowed"""
    try:
      Song.objects.get(sha_hash=upload.info['sha_hash'])
    except Song.DoesNotExist: pass
    else:
      self.user.message_set.create(message="The dong '%s' is already in the database" % upload.info['title'])
      raise DuplicateError, "song already in database"
    
    if os.path.getsize(upload.file) > settings.MAX_UPLOAD_SIZE:
      self.user.message_set.create(message="The dong %s too big" % upload.info['title'])
      raise FileTooBigError
    
    upload.info['uploader'] = self.user
    s = upload.store()
    
    if s.length > settings.MAX_SONG_LENGTH: #10 mins
      s.ban("Autobahned because the dong is too long. Ask a mod to unban it if you want to play it.")
    s.save()
    
    self.user.get_profile().uploads += 1
    self.user.save()
      
  def addDisallowed(self, entries=None):
    #check user hasn't got too many songs on the playlist
    if not entries:
      entries = PlaylistEntry.objects.all()
    if len(entries.filter(adder=self.user)) >= int(settings.PLAYLIST_MAX):
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
    #d['filesize'] = file.size
    
    if not ("title" in d.keys()):
      d['title'] = file.name
    if 'artist' in d.keys():
      d['artist'] = utils.getObj(Artist, d['artist'])
    else:
      d['artist'] = utils.getObj(Artist, "unknown")
    if 'album' in d.keys():
      d['album'] = utils.getObj(Album, d['album'])
    else:
      d['album'] = utils.getObj(Album, "unknown")
      
    for x in ["tracknumber", "version", "date"]:
      if x in d.keys():
        del d[x]      
    
    d['format'] = "mp3"
    
    return d
    
  def canDelete(self, song):
    if self.user.has_perm('playlist.delete_song'):
      return True
    if PlaylistEntry.objects.filter(song=song) or OldPlaylistEntry.objects.filter(song=song):
      return False #on playlist
    td = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    if (now < song.add_date+td) and (self.user == song.uploader):
      return True
    return False
  
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
    ("view_user",  "g2 Can view user pages"), 
    )

  def __unicode__(self): return self.user.username
  
class ChatboxPost(models.Model):
  user = models.ForeignKey(User)
  postdate = models.DateTimeField()
  post = models.CharField(max_length=300)
  

#class StreamOptions(dbsettings.Group):
  #pid  = dbsettings.PositiveIntegerValue()
  


class SongSet(QuerySet):
  """Extends QuerySet for aggregated song checking methods"""
  
#  def __init__(self, model=None):
#    super(SongSet, self).__init__(model)
         
  def check_playable(self, user):
    
    #song already on playlist
    playlist = 'SELECT COUNT(*) FROM playlist_playlistentry \
            WHERE playlist_playlistentry.song_id = playlist_song.id'
            
    #song too recently played
    recent = '(SELECT count(*) FROM playlist_oldplaylistentry \
              WHERE (playlist_oldplaylistentry.song_id = playlist_song.id) AND \
              (playlist_oldplaylistentry.playtime-0 > NOW()-INTERVAL %d HOUR))' % (settings.REPLAY_INTERVAL)
    
    select = {#'is_banned' : 'banned = 1',
              #'on_playlist' : playlist,
              'recently_played': recent,
              }
    return super(SongSet, self).annotate(on_playlist=Count('entries')).\
                                          extra(select=select)
  
class SongManager(models.Manager):
  def get_query_set(self):
    return SongSet(self.model)  #force Song to use extended queryset
  

class Song(models.Model):
  #TODO: sort out artist/composer/lyricist/remixer stuff as per note
  title = models.CharField(max_length=300)
  artist = models.ForeignKey(Artist, blank=True, related_name='songs')
  album = models.ForeignKey(Album, blank=True, related_name='songs')
  composer = models.CharField(max_length=300, blank=True) #balthcat <3
  lyricist = models.CharField(max_length=300, blank=True)
  remixer = models.CharField(max_length=300, blank=True) #balthcat <3
  genre = models.CharField(max_length=100, blank=True)
  length = models.IntegerField(editable=False) #in seconds
  bitrate = models.IntegerField(editable=False) #in kbps
  sha_hash = models.CharField(max_length=40, unique=True, editable=False)
  add_date = models.DateTimeField(editable=False)
  format = models.CharField(max_length=3, editable=False)
  uploader = models.ForeignKey(User, editable=False, related_name="uploads")
  category = models.CharField(max_length=20, default="regular", editable=False)
  
  banned = models.BooleanField(default=False, editable=False)
  banreason = models.CharField(max_length=100, blank=True, editable=False)
  unban_adds = models.IntegerField(default=0, editable=False) #number of plays till rebanned: 0 is forever
  
  location = models.ForeignKey("SongDir", null=True, editable=False)
  
  avgscore = models.FloatField(default=0, editable=False)
  voteno = models.IntegerField(default=0, editable=False)
  # ratings, comments, entries & oldentries are related_names
  
  
  objects = SongManager()
  #stream_options = StreamOptions()
  
  def addDisallowed(self):
    """Returns (reason, shortreason) tuple. 
    Reason for user, shortreason for add button.
    More effcient & comprehensive if called on queryset returned from check_playable
    Otherwise returns False.
    """
    try:
      if self.on_playlist:
         return ("song already on playlist", "on playlist")
      if self.recently_played:
        return ("song played too recently", "recently played")
      if self.banned:
        return ("song banned", "banned")
#      elif self.greedy_user:
#        return ("you already have too many songs on the playlist", "user is greedy")
    except:
      if self.banned:
        return ("song banned", "banned")
      if len(PlaylistEntry.objects.filter(song=self)) > 0:
        return ("song already on playlist", "on playlist")
      #check song hasn't been played recently: dt is definition of 'recently'
      dt = datetime.datetime.now()-datetime.timedelta(hours=int(settings.REPLAY_INTERVAL))
      if len(OldPlaylistEntry.objects.filter(song=self, playtime__gt=dt)) > 0:
        return ("song played too recently", "recently played")
    
    return False
      
  def isOrphan(self):
    scuttle = User.objects.get(username="Fagin")
    if self.uploader == scuttle:
      return True
    
  def playlistAdd(self,  user):
    """Adds song to the playlist. 
    Raises AddError if there's a problem, with (reason, shortreason) as its arg."""
    
    reasons = self.addDisallowed()
    if reasons:
      reason, shortreason = reasons
      raise AddError, (reason, shortreason)
    reasons = user.get_profile().addDisallowed()
    if reasons:
      reason, shortreason = reasons
      raise AddError, (reason, shortreason)
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
  
  def getPath(self):
    return self.location.genPath(self.sha_hash, self.format)
  
  def ban(self, reason=""):
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
      return u"%s (%s) - %s" % (self.artist, self.album, self.title)
    
  def rate(self, score, user):
    score = float(score)
    if not ((1 <= score and score <= 5) or (score==0)):
      raise ScoreOutOfRangeError
    
    try:
      r = Rating.objects.get(user=user, song=self)
      prevscore = r.score
      if score == 0: #0 is delete
        r.delete()
      else:  
        r.score = score
        r.save()
    except Rating.DoesNotExist:
      #not yet created (yes I know this is what get_or_create is for but it's stupid
      #(it can't do required fields properly))
      prevscore = 0
      if score != 0: #0 is delete, don't create instead
        r = Rating(user=user, song=self, score=score)
        r.save()
    #sort out statistics
    stats = Rating.objects.filter(song=self).aggregate(id_count=Count('id'), avg_score=Avg('score'))
    if (not stats['id_count']) or (not stats['avg_score']):
      self.voteno = self.avgscore = 0
    else:
      self.voteno = stats['id_count'] #Rating.objects.filter(song=self).count()
      #ratings = [rating['score'] for rating in Rating.objects.filter(song=self).values()]
      self.avgscore = stats['avg_score'] #sum(ratings) / self.voteno
    self.save()
    return prevscore
    
  def comment(self, user, comment):
   
    if PlaylistEntry.objects.nowPlaying().song == self:
      cue = CueFile(settings.LOGIC_DIR + "/ices.cue")
      time = cue.getTime(self)
    else:
      time = 0
    c = Comment(text=comment, user=user, song=self, time=time)
    c.save()    
    
  def save(self):
    #ensure add_date is creation date
    if not self.id:
        self.add_date = datetime.datetime.today()
    super(Song, self).save()
    
  def delete(self):
    #prune artist if now empty
    if self.artist.songs.count() <= 1:
        self.artist.delete()
    super(Song, self).delete()

  class Meta:
    permissions = (
    ("view_song",  "g2 Can view song pages"), 
    ("upload_song",  "g2 Can upload songs"),
    ("ban_song",  "g2 Can ban songs"),
    ("edit_song", "g2 Can edit all songs."),
    ("delete_song", "g2 Can delete all songs."),
    ("start_stream", "g2 Can start the stream."),
    ("stop_stream", "g2 Can stop the stream"),
    ("view_g2admin", "g2 Can view g2 Admin page."),
    )
    

class SongDirManager(models.Manager):

  
  def getUsableDir(self):
    """Return the first directory object we can find that's usable"""
    
    return super(SongDirManager, self).filter(usable=True)[0]

    



class SongDir(models.Model):
  """Represents a directory for storing song files in"""
  #absolute path to directory 
  path = models.CharField(max_length=300)
  #number of letters of file hash to use for subdirectories. 0 means no subdirectories
  hash_letters = models.IntegerField()
  #True if accepting new uploads
  usable = models.BooleanField(default=True)
  
  objects = SongDirManager()
  
  def storeSong(self, temp_path, info):
    
    new_file = open(self.genPath(info['sha_hash'], info['format']),  'w')
    temp_file = open(temp_path)
    try:
      new_file.write(temp_file.read())
    finally:
      temp_file.close() #Django temp file so no need to delete
      new_file.close()
    
  def genPath(self, sha_hash, format):
    hash_dir = sha_hash[0:self.hash_letters] #get appripriate number of hash digits
    return self.path+'/'+ hash_dir + '/' + sha_hash + '.' + format
      
      

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
  class Meta:
    ordering = ['-datetime']
    permissions = (
    ("can_comment",  "g2 Can comment on songs"),
    )

    
class PlaylistManager(models.Manager):
  
  def length(self):
    """Returns dictionary of playlist length in seconds and song count."""
    return super(PlaylistManager, self).select_related('song').filter(playing=False).aggregate(seconds=Sum('song__length'), song_count=Count('song'))
    
  def nowPlaying(self):
    return super(PlaylistManager, self).get(playing=True)
  

    
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
    except IndexError:
      #no more songs :(
      #oh well, repeat this one and *don't* record it as having played
      #old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
      #old.save()
      #self.playtime=datetime.datetime.today()
      return self
      
    new.playing = True
    new.playtime = datetime.datetime.today()
    #record old one
    old = OldPlaylistEntry(song=self.song, adder=self.adder, addtime=self.addtime, playtime=self.playtime)
    old.save()
    self.delete()
    new.save()
    return new

  def remove(self):
    """removes from playlist and lets ajax playlist handler know"""
    RemovedEntry(oldid=self.id).save()
    self.delete()
  
  def save(self):
    if not self.id:
        self.addtime = datetime.datetime.today()
    super(PlaylistEntry, self).save()
    
  def __unicode__(self): return self.song.title
  
  def delSong(self, songid):
    self.entries.objects.get(id=songid).delete()
    self.save()
    
  objects = PlaylistManager()
      
  class Meta:
    ordering = ['-playing', '-hijack', 'addtime']
    permissions = (
    ("view_playlist",  "g2 Can view the playlist"), 
    ("queue_song",  "g2 Can add song to the playlist"), #golden_appel <3
    ("remove_entry", "g2 Can remove all playlist entries"),
    ("skip_song", "g2 Can skip currently playing song")
    ) 
    verbose_name_plural = "Playlist"
    
class RemovedEntry(models.Model):
  oldid = models.IntegerField()
  creation_date = models.DateTimeField()
  
  def save(self):
    if not self.id: #populate creation date
        self.creation_date = datetime.datetime.today()
    super(RemovedEntry, self).save()
    
class OldPlaylistEntry(models.Model):
  song = models.ForeignKey(Song, related_name="oldentries")
  adder = models.ForeignKey(User)
  addtime = models.DateTimeField()
  playtime = models.DateTimeField()
  skipped = models.BooleanField(default=False)
    
  class Meta:
    ordering = ['id']

class Settings(models.Model):
  key = models.CharField(max_length=200)
  value = models.CharField(max_length=3000)
  
  def __unicode__(self): return self.key
  
  class Meta:
    ordering = ['key']


####### DJ Shows ########

class Series(models.Model):
  name = models.CharField(max_length=200)
  short_name = models.CharField(max_length=15)
  description = models.CharField(max_length=2500)
  
  def __unicode__(): unicode(short_name)

class Show(models.Model):
  """A DJ show scheduled for the future"""
  start_time = models.DateTimeField()
  end_time = models.DateTimeField()
  owner = models.ForeignKey(User, related_name="shows")
  name = models.CharField(max_length=200)
  description = models.CharField(max_length=2500)
  reschedule = models.BooleanField()
  series = Series

class OldShow(models.Model):
  """Recorded show. Also used for current shows"""
  start_time = models.DateTimeField(blank=True, null=True)
  end_time = models.DateTimeField(blank=True, null=True)
  owner = models.ForeignKey(User, related_name="oldshows")
  name = models.CharField(max_length=200)
  description = models.CharField(max_length=2500)
  playing = models.BooleanField(default=True)
  
class ShowRating(models.Model):
  score = models.FloatField()
  user = models.ForeignKey(User, related_name='show_ratings', unique=True)
  show = models.ForeignKey(OldShow, related_name='ratings')
  
  def __unicode__(self): return unicode(self.rating)
  
  class Meta:
    unique_together = ('user', 'show')
    

class ShowComment(models.Model):
  text = models.CharField(max_length=400)
  user = models.ForeignKey(User, editable=False, related_name="show_comments")
  show = models.ForeignKey(OldShow, editable=False, related_name="comments")
  time = models.DateTimeField()
  
  def save(self):
    #ensure datetime is creation date
    if not self.id:
        self.datetime = datetime.datetime.today()
    super(Comment, self).save()
  class Meta:
    ordering = ['-time']

class ShowMinute(models.Model):
  """Minutely recording of various show statistics"""
  show = models.ForeignKey(OldShow, related_name="minutes")
  time = models.DateTimeField()
  listeners = models.IntegerField()
  metadata = models.CharField(max_length=300)
  avg_score = models.FloatField()
  

def randomdongid():
    from django.db import connection, transaction
    cursor = connection.cursor()

    # Data retrieval operation - no commit required
    cursor.execute("SELECT * from public_data.random_dongid")
    row = cursor.fetchone()

    return row
  
def plinfoq(self):
    from django.db import connection, transaction
    cursor = connection.cursor()

    # Data retrieval operation - no commit required
    cursor.execute("select song.id, song.title, artist.name, album.name from playlist_song song, playlist_artist artist, playlist_album album where song.artist_id = artist.id and song.album_id = album.id and song.id = (SELECT song_id FROM `gbsfm`.`playlist_playlistentry` order by id limit %s,1)", [int(self)])
    row = cursor.fetchone()
    return row



  

