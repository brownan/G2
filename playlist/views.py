# -*- coding: utf-8 -*-

    #######################################################################
    # This file is part of the g2 project.                                #
    #                                                                     #
    # g2 is free software: you can redistribute it and/or modify          #
    # it under the terms of the Affero General Public License, Version 1, #
    # as published by Affero, Incorporated, but not any later             #
    # version.                                                            #
    #                                                                     #
    # g2 is distributed in the hope that it will be useful,               #
    # but WITHOUT ANY WARRANTY; without even the implied warranty of      #
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the        #
    # Affero General Public License for more details.                     #
    #                                                                     #
    # You can find a copy of the Affero General Public License, Version 1 #
    # at http://www.affero.org/oagpl.html.                                #
    #######################################################################

import os
import signal
import itertools
import datetime
from random import getrandbits
from hashlib import md5
from urllib2 import urlopen, URLError
import urllib2
import cookielib
from urllib import quote, urlencode
from subprocess import Popen
import logging

from django.http import HttpResponse,  HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import Context, loader
from django.core.urlresolvers import reverse
from django.core.serializers import serialize
from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render_to_response
import django.contrib.auth.views
import django.contrib.auth as auth
from django.forms.models import modelformset_factory
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import RequestContext
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Avg, Max, Min, Count
from django.contrib.auth import authenticate
from django.db import connection

from pydj.playlist.models import *
from pydj.playlist.utils import getSong, getObj, listenerCount
from pydj.playlist.upload import UploadedFile


permissions = ["upload_song", "view_artist", "view_playlist", "view_song", "view_user", "queue_song"]

PIDFILE = settings.LOGIC_DIR+"/pid"
SA_PREFIX = "http://forums.somethingawful.com/member.php?action=getinfo&username="
LIVE = settings.IS_LIVE

from django.contrib.auth.decorators import permission_required, login_required

def now():
  return " ".join(datetime.datetime.now().isoformat().split("T"))

class UploadFileForm(forms.Form):
  file  = forms.FileField()

class SearchForm(forms.Form):
  query = forms.CharField(max_length=100)
  orphan = forms.BooleanField(required=False, initial=False)
  
  def clean_query(self):
    if len(self.cleaned_data['query']) < 3:
      raise forms.ValidationError, "Query should be 3 characters long or more."
    return self.cleaned_data['query']
  
class SongForm(forms.ModelForm):

  artist = forms.CharField(max_length=300) #replace dropdowns with charfields
  album = forms.CharField(max_length=300) #they should be filled in the template 
  class Meta:
    model = Song
    #exclude = ("album", "artist")
    
  def populate(self, song):pass
    #self.artist = forms.CharField(max_length=300, initial=song.artist.name)
    #self.album = forms.CharField(max_length=300, initial=song.album.name)
  
  def save(self):
    self.cleaned_data['artist'] = getObj(Artist, self.cleaned_data['artist'], self.initial['artist']) #convert strings to objects
    self.cleaned_data['album'] = getObj(Album, self.cleaned_data['album'])
    forms.ModelForm.save(self)
  

class SettingsForm(forms.ModelForm):
  class Meta:
    #model = UserProfile
    fields = ()
    
#class SearchForm(forms.Form):
 # pass
    
class CommentForm(forms.Form):
  comment = forms.CharField(max_length=400)
  
class BanForm(forms.Form):
  reason = forms.CharField(max_length=100)
  
class RegisterForm(UserCreationForm):
  passcode = forms.CharField(max_length=50)

  
class NewRegisterForm(forms.Form):
  saname = forms.CharField(max_length=30, label="SA Username:")
  password1 = forms.CharField(max_length=30, label="Desired Password:", widget=forms.PasswordInput)
  password2 = forms.CharField(max_length=30, label="Confirm Password:", widget=forms.PasswordInput)
  email = forms.EmailField(label="E-mail Address:")
  randcode = forms.CharField(max_length=32, widget=forms.HiddenInput)
      
  def clean(self):
    if self.cleaned_data['password1'] != self.cleaned_data['password2']:
      raise forms.ValidationError, "Passwords must match"
    if len(self.cleaned_data['password1']) < 4:
      raise forms.ValidationError, "Password too short: must be at least 4 characters"
    
    return self.cleaned_data
  
  def clean_saname(self):
    try:
      User.objects.get(username=self.cleaned_data['saname'])
      raise forms.ValidationError, "Username already registered. If you're not happy about this, PM Jonnty."
    except User.DoesNotExist:
      return self.cleaned_data['saname'] 
      
  
class WelcomeMsgForm(forms.Form):
  message = forms.CharField(max_length=2000, widget=forms.Textarea)

  
@permission_required('playlist.start_stream')
def start_stream(request):
  utils.start_stream()
  return HttpResponseRedirect(reverse('g2admin'))

@permission_required('playlist.stop_stream')
def stop_stream(request):
  utils.stop_stream()
  return HttpResponseRedirect(reverse('g2admin'))  
  
@permission_required('playlist.view_g2admin')
def g2admin(request):
  if request.method == "POST":
    msgform = WelcomeMsgForm(request.POST)
    if msgform.is_valid():
      msg = Settings.objects.get(key="welcome_message")
      msg.value = msgform.cleaned_data['message']
      msg.save()  
  else:
    msgform = WelcomeMsgForm(initial={'message':Settings.objects.get(key="welcome_message").value})
  return render_to_response('admin.html',  {"msgform":msgform}, context_instance=RequestContext(request))
  
def splaylist(request):
  #for scuttle loadtesting
  try:
    if authenticate(username=request.REQUEST['username'], password=request.REQUEST['password']):
      return jsplaylist(request)
  except KeyError: pass
  return HttpResponseRedirect(reverse('login'))
    
@permission_required('playlist.view_playlist')
def playlist(request):
  #normal entry route
  return jsplaylist(request)
  
  
def jsplaylist(request):
  try:
    historylength = request.user.get_profile().s_playlistHistory
  except AttributeError:
    historylength = 10
  #historylength = 10
  oldentries = OldPlaylistEntry.objects.all()
  playlist = itertools.chain(oldentries.extra(where=['playlist_oldplaylistentry.id > \
  (select max(id) from playlist_oldplaylistentry)-%s'], params=[historylength], 
  select={"user_vote": "SELECT score FROM playlist_rating WHERE playlist_rating.user_id = %s AND playlist_rating.song_id = playlist_oldplaylistentry.song_id"},
  select_params=[request.user.id]).select_related(), 
  PlaylistEntry.objects.extra(select={"user_vote": "SELECT score FROM playlist_rating WHERE playlist_rating.user_id = \
  %s AND playlist_rating.song_id = playlist_playlistentry.song_id"},
  select_params=[request.user.id]).select_related("song__artist", "song__album", "song__uploader", "adder").all().order_by('addtime'))
  aug_playlist= []
  for entry in playlist:
    if isinstance(entry, PlaylistEntry) and not entry.playing and (request.user.has_perm('remove_entry') or request.user == entry.adder):
      aug_playlist.append({'can_remove':True, 'object':entry, 'pl':True})
    elif isinstance(entry, PlaylistEntry):
      aug_playlist.append({'can_remove':False, 'object':entry, 'pl':True})
    else:
      aug_playlist.append({'can_remove':False, 'object':entry, 'pl':False})
    
  can_skip = request.user.has_perm('playlist.skip_song')
  now_playing = PlaylistEntry.objects.get(playing=True).song.metadataString()
  lastremoval = RemovedEntry.objects.aggregate(Max('id'))['id__max']
  try:
    welcome_message = Settings.objects.get(key="welcome_message").value
  except:
    welcome_message = None
  
  
  return render_to_response('jsplaylist.html',  {'aug_playlist': aug_playlist, 'can_skip':can_skip, 'lastremoval':lastremoval, 'now_playing':now_playing, 'welcome_message':welcome_message}, context_instance=RequestContext(request))

  
 # return render_to_response('index.html',  {'aug_playlist': aug_playlist, 'msg':msg, 'can_skip':can_skip}, context_instance=RequestContext(request))
  
  
def ajax(request, resource=""):
  
  #authentication
  if request.user.is_authenticated():
    user = request.user
  else: #non-persistent authentication for things like bots and clients
    try:
      username = User.objects.get(id=request.REQUEST['userid']).username
    except User.DoesNotExist:
      raise Http404
    except KeyError: 
      try:
        username = request.REQUEST['username']
        password = request.REQUEST['password']
      except KeyError:
        raise Http404
    user = authenticate(username=username, password=password)
    if user is None:
      #incorrect login details
      return HttpResponseForbidden()
    
  if resource == "nowplaying":
    entryid = PlaylistEntry.objects.get(playing=True).id
    return HttpResponse(str(entryid))
    
  #if resource == "olsequence":
    #historylength = request.user.get_profile().s_playlistHistory
    #oldentries = OldPlaylistEntry.objects.all()
    #if historylength <= oldentries.count():
      #oldlist = list(oldentries[oldentries.count()-historylength:])
    #else:
      #oldlist = list(oldentries)
    #data = serialize("json", oldlist, fields=('id'))
    #return HttpResponse(data)
      
  #if resource == "plsequence":
    #playlist = PlaylistEntry.objects.all()
    #oldentries = OldPlaylistEntry.objects.all()
    #data = serialize("json", playlist, fields=('id', 'playing'))
    #return HttpResponse(data)
  
  if resource == "deletions":
    try:
      lastid = request.REQUEST['lastid']
    except KeyError:
      lastid = 0
    if not lastid: lastid = 0
    deletions = RemovedEntry.objects.filter(id__gt=lastid)
    data = serialize("json", deletions, fields=('oldid'))
    return HttpResponse(data)

  if resource == "adds":
    try:
      lastid = request.REQUEST['lastid']
    except KeyError:
      lastid = 0
    if not lastid: lastid = 0
    deletions = PlaylistEntry.objects.select_related().filter(id__gt=lastid)
    data = serialize("json", deletions, relations={'song':{'relations':('artist'), 'fields':('title', 'length', 'artist')}, 'adder':{'fields':('username')}})
    return HttpResponse(data)
    
  if resource == "history":
    try:
      lastid = request.REQUEST['lastid']
    except KeyError:
      raise Http404
    if not lastid: raise Http404
    if lastid[0] != 'h':
      raise Http404 #avert disaster
    lastid = lastid[1:] #get rid of leading 'h'
    history = OldPlaylistEntry.objects.select_related().filter(id__gt=lastid)
    data = serialize("json", history, relations={'song':{'relations':('artist'), 'fields':('title', 'length', 'artist')}, 'adder':{'fields':('username')}})
    return HttpResponse(data)
  
  if resource == "pltitle":
    return HttpResponse(PlaylistEntry.objects.get(playing=True).song.metadataString() + " - GBS-FM")
  
  if resource == "vote":
    try:
      vote = int(request.REQUEST['vote'])
    except KeyError:
      raise Http404
    try:
      songid = request.REQUEST['songid']
      songid = int(songid)
      song = Song.objects.get(id=songid)
    except KeyError:
      song = PlaylistEntry.objects.get(playing=True).song
    except ValueError:
      if songid == "curr":
        song = PlaylistEntry.objects.select_related("song").get(playing=True).song
      elif songid == "prev":
        song = OldPlaylistEntry.objects.select_related("song").extra(where=['playlist_oldplaylistentry.id =\
        (select max(playlist_oldplaylistentry.id) from playlist_oldplaylistentry)'])[0].song
    prevscore = song.rate(vote, user)
    
    return HttpResponse(str(prevscore) + " " +song.metadataString())
  
  if resource == "listeners":
    return HttpResponse(listenerCount())
    
  raise Http404

@login_required()
def removeentry(request, entryid):
  entry = PlaylistEntry.objects.select_related().get(id=entryid)
  if ((entry.adder == request.user) or request.user.has_perm("playlist.remove_entry")) and not entry.playing:
    logging.info("User %s (uid %d) removed songid %d from playlist at %s" % (request.user.username, request.user.id, entry.song.id, now()))
    entry.delete()
    request.user.message_set.create(message="Entry deleted successfully.")
  else:
    request.user.message_set.create(message="Error: insufficient permissions to remove entry")
  if request.is_ajax():
    return HttpResponse(str(success))
  else:
    return HttpResponseRedirect(reverse('playlist'))
  
@permission_required('playlist.skip_song')
def skip(request):
  logging.info("Mod %s (uid %d) skipped song at %s" % (request.user.username, request.user.id, now()))
  Popen(["killall", "-SIGUSR1", "ices"])
  return HttpResponseRedirect(reverse('playlist'))

@permission_required('playlist.view_song')
def song(request, songid=0, edit=None):
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    return render_to_response('song.html', {'error': 'Song not found.'})
  if request.method == "POST" and (request.user.has_perm('playlist.edit_song') or (request.user == song.uploader)):
    editform = SongForm(request.POST, instance=song)
    if editform.is_valid():
      editform.save()
  else:
    editform = SongForm(instance=song)
  commentform = CommentForm()
  comments = Comment.objects.filter(song=song)
  banform = BanForm()
  can_ban = request.user.has_perm('playlist.ban_song')
  if request.user.get_profile().canDelete(song):
    can_delete = True
  else:
    can_delete = False
  if request.user.has_perm('playlist.edit_song') or (request.user == song.uploader):
    can_edit = True
  else:
    can_edit = False
    edit = None
  try:
    vote = Rating.objects.get(user=request.user, song=song).score
  except Rating.DoesNotExist:
    vote = 0
  if request.user.has_perm('playlist.edit_song'):
    path = song.getPath()
  else:
    path = None
  
  is_orphan = (song.uploader == User.objects.get(username="Fagin"))
    
    
  
  return render_to_response('song.html', \
  {'song': song, 'editform':editform, 'edit':edit,'commentform':commentform, \
  'currentuser':request.user, 'comments':comments, 'can_ban':can_ban, 'is_orphan':is_orphan, \
  'banform':banform, 'can_delete':can_delete, 'can_edit':can_edit, 'vote':vote, 'path':path,}, \
  context_instance=RequestContext(request))

  
@login_required()
def listartists(request, letter='123', page='1'):
  def the_filter(e):
    if len(e.name) > 4:
      return (not e.name[0].isalpha()) or (e.name[:4].lower() == "the" and (not e.name[4].isalpha()))
    elif len(e.name) == 0:
      return False
    else:
      return not e.name[0].isalpha()
      
  def sortkey(x):
    if len(x.name) > 4:
      return x.name[:4].lower()=="the " and x.name[4:].lower() or x.name.lower()
    else:
      return x.name.lower()
  letter = letter.lower()
  #artists = Artist.objects.all().order_by("name")
  
  #for artist in artists:
    #if artist.songs.count() == 0:
      #artist.delete() #prune empty artists
      
  if letter == '123':
    artists = Artist.objects.all().order_by("sort_name").annotate(song_count=Count('songs'))
    artists = filter(the_filter, artists)
  elif letter == "all":
    artists = Artist.objects.all().order_by("sort_name").annotate(song_count=Count('songs'))
  elif letter.isalpha():
    artists = Artist.objects.filter(sort_name__istartswith=letter).order_by("sort_name").annotate(song_count=Count('songs'))
  else:
    raise Http404
  #artists = list(artists)
  #artists.sort(key=sortkey) #sort 'the's properly
  try:
    page = int(page)
  except:
    page = 1
  p = Paginator(artists, 50)
  try:
    artists = p.page(page)
  except (EmptyPage, InvalidPage):
    #page no. out of range
    artists = p.page(p.num_pages)
  return render_to_response('artists.html', {"artists": artists, "letter": letter}, context_instance=RequestContext(request))

  
@permission_required('playlist.ban_song')
def bansong(request, songid=0):
  if request.method == "POST":
    form = BanForm(request.POST)
    if form.is_valid():
      song = Song.objects.get(id=songid)
      reason = form.cleaned_data['reason']
      song.ban(reason)
      song.save()
      logging.info("Mod %s (uid %d) banned songid %d with reason '%s' at %s" % (request.user.username, request.user.id, song.id, reason, now()))
      
  return HttpResponseRedirect(reverse('song', args=[songid]))

@permission_required('playlist.ban_song')
def unbansong(request, songid=0, plays=0):
  song = Song.objects.get(id=songid)
  song.unban(plays)
  logging.info("Mod %s (uid %d) unbanned songid %d for %d plays at %s" % (request.user.username, request.user.id, song.id, int(plays), now()))
  return HttpResponseRedirect(reverse('song', args=[songid]))

@login_required()
def deletesong(request, songid=0):
  """Deletes song with songid from db. Does not yet delete file."""
  song = Song.objects.get(id=songid)
  if request.user.get_profile().canDelete(song):
    logging.info("User %s (uid %d) deleted song '%s' with hash %s at %s" % (request.user.username, request.user.id, 
                                                                        song.metadataString(), song.sha_hash, now()))
    song.delete()
    return HttpResponseRedirect(reverse(playlist))
  else:
    request.user.message_set.create(message="Error: you are not allowed to delete that song")
    return HttpResponseRedirect(reverse('song', args=[songid]))
  
@login_required()
def user(request, userid):
  owner=  User.objects.get(id=userid)
  return render_to_response("user.html", {'owner':owner}, context_instance=RequestContext(request))

@permission_required('playlist.can_comment')
def comment(request, songid): 
  song = Song.objects.get(id=songid)
  if request.method == "POST":
    form = CommentForm(request.POST)
    if form.is_valid():
      #TODO: include song time
      song.comment(request.user, form.cleaned_data['comment'])
  return HttpResponseRedirect(reverse('song', args=[songid]))


@permission_required('playlist.can_rate')
def rate(request, songid, vote):
  song = Song.objects.get(id=songid)
  song.rate(vote, request.user)
  return HttpResponseRedirect(reverse('song', args=[songid]))

@permission_required('playlist.upload_song')
def upload(request):
  if request.method == "POST":
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      f = request.FILES['file']
      try:
        request.user.get_profile().uploadSong(UploadedFile(f.temporary_file_path(), f.name))
      except DuplicateError:
        request.user.message_set.create(message="Error: track already uploaded")
      except FileTooBigError:
        message = request.user.message_set.create(message="Error: file too big")
      else:
        request.user.message_set.create(message="Uploaded file successfully!")
  else:
    form = UploadFileForm()
  uploads = Song.objects.select_related().filter(uploader=request.user).order_by("-add_date")
  if len(uploads) > 10: 
    recentuploads = uploads[:10]
  else: 
    recentuploads = uploads
  return render_to_response('upload.html', {'form': form, 'uploads':recentuploads}, context_instance=RequestContext(request))


@permission_required('playlist.view_artist')
def artist(request, artistid=None):
  artist = Artist.objects.get(id=artistid)
  songs = Song.objects.select_related().filter(artist=artist).order_by("album__name")
  return render_to_response("artist.html", {'songs': songs, 'artist': artist}, context_instance=RequestContext(request))
    
@permission_required('playlist.queue_song')
def add(request, songid=0): 
  try:
    song = Song.objects.get(id=songid)
    song.playlistAdd(request.user)
  except AddError, e:
    msg = "Error: %s" % (e.args[0])
    request.user.message_set.create(message=msg)
    return HttpResponseRedirect(reverse("playlist"))      
  else:
    scuttle = User.objects.get(username="Fagin")
    if song.uploader == scuttle:
      song.uploader = request.user
      song.save()
      request.user.message_set.create(message="This dong was an orphan, so you have automatically adopted it. Take good care of it!")
    request.user.message_set.create(message="Track added successfully!")
    if settings.DEBUG:
      f = open(settings.LOG_DIR + "/sql.log", "a")
      f.write("---\n")
      for q in connection.queries:
        f.write(q['time'] + " : " + q['sql'] + '\n')
      f.close()
    return HttpResponseRedirect(reverse("playlist"))
  
def next(request, authid):
  if authid == settings.NEXT_AUTHID:
    try:
      entry = PlaylistEntry.objects.get(playing=True).next()
      location = getSong(entry.song)
      metadata = u"%s [blame %s]" % (entry.song.metadataString(request.user), entry.adder.username)
      return HttpResponse(location +'\n'+ metadata)
    except PlaylistEntry.DoesNotExist:
      pass
  return HttpResponse()

def register(request):
  if request.method == "POST":
    form = RegisterForm(request.POST, request.FILES)
    if form.is_valid():
      if form.cleaned_data['passcode'] != 'dongboners':
        error = "Incorrect passcode"
        return render_to_response('register.html', {'form': form, 'error':error})
      username = form.cleaned_data['username']
      password = form.cleaned_data['password1']
      user = User.objects.create_user(username=username, email="", password=password)
      try: g = Group.objects.get(name="Listener")
      except Group.DoesNotExist:
        g = Group(name="user")
        g.save()
        [g.permissions.add(Permission.objects.get(codename=s)) for s in permissions]
        g.save()
      user.groups.add(g)
      user.save()
      UserProfile(user=user).save()
      return HttpResponseRedirect(reverse(django.contrib.auth.views.login))
  else:
    form = RegisterForm()
    error = "Fill in the form properly"
  return render_to_response('register.html', {'form': form}, context_instance=RequestContext(request))
   

   
def newregister(request):
  get_authcode = lambda randcode: md5(settings.SECRET_KEY + randcode).hexdigest()
  get_randcode = lambda: md5(str(getrandbits(64))).hexdigest()
  error = ""
  if request.method == "POST":
    
    form = NewRegisterForm(request.POST)
    if form.is_valid():
      randcode = form.cleaned_data['randcode']
      try:
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
        opener.open("http://forums.somethingawful.com/account.php", \
                    urlencode([("username", settings.SA_USERNAME), ("password", settings.SA_PASSWORD), ("action", "login")]))
        if not get_authcode(form.cleaned_data['randcode']) in \
           opener.open(SA_PREFIX + quote(form.cleaned_data['saname'])).read() and LIVE:
          error = "Verification code not found on your profile."
      except URLError:
        error = "Couldn't find your profile. Check you haven't made a typo and that SA isn't down."
      if not error:
        username = form.cleaned_data['saname']
        password = form.cleaned_data['password1']
        email = form.cleaned_data['email']
        user = User.objects.create_user(username=username, email=email, password=password)
        try: g = Group.objects.get(name="Listener")
        except Group.DoesNotExist:
          g = Group(name="Listener")
          g.save()
          [g.permissions.add(Permission.objects.get(codename=s)) for s in permissions]
          g.save()
        user.groups.add(g)
        user.save()
        UserProfile(user=user).save()
        return HttpResponseRedirect(reverse(django.contrib.auth.views.login))
    else:
      randcode = request.POST['randcode']
  else:
    randcode = get_randcode()
    form = NewRegisterForm(initial={'randcode': randcode})
  authcode = get_authcode(randcode)
  return render_to_response('register.html', {'form': form, 'authcode': authcode, 'error':error}, context_instance=RequestContext(request))
  
@login_required()
def search(request):
  if request.method == 'POST': # If the form has been submitted...
    form = SearchForm(request.POST) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      query = form.cleaned_data['query']
      
      artists = Artist.objects.select_related().filter(name__icontains=query).order_by('name')
      songs = Song.objects.select_related().filter(title__icontains=query).order_by('title')
      if form.cleaned_data['orphan']:
        scuttle = User.objects.get(username="Fagin")
        orphans = songs.filter(uploader=scuttle).order_by('title')
        temp = []
        for artist in artists:
          for song in artist.songs.all():
            if song.uploader == scuttle:
              temp.append(artist)
              break
        artists = temp
        songs = orphans
        
      return render_to_response('search.html', {'form':form, 'artists':list(artists), 'songs':songs, 'query':query},\
      context_instance=RequestContext(request))
  else:
    form = SearchForm()
  return render_to_response('search.html', {'form':form}, context_instance=RequestContext(request))


def info(request):
  song = PlaylistEntry.objects.get(playing=True)
  return HttpResponse()

@login_required()
def orphans(request, page=0):
  try:
    page = int(page)
  except:
    page = 1
  scuttle = User.objects.get(username="Fagin")
  songs = Song.objects.filter(uploader=scuttle).order_by("title")
  for song in songs: 
    p = Paginator(songs, 50)
  try:
    songs = p.page(page)
  except (EmptyPage, InvalidPage):
    #page no. out of range
    songs = p.page(p.num_pages)
  return render_to_response('scuttle.html', {"songs": songs}, context_instance=RequestContext(request))

@login_required()
def adopt(request, songid):
  song = Song.objects.get(id=songid)
  scuttle = User.objects.get(username="Fagin")
  if not song in Song.objects.filter(uploader=scuttle):
    request.user.message_set.create(message="You may not adopt this dong.")
    return HttpResponseRedirect(reverse("song", args=[songid]))
  else:
    song.uploader = request.user
    song.save()
    request.user.message_set.create(message="Dong adopted successfully. Take good care of it!")
    return HttpResponseRedirect(reverse("song", args=[songid]))    
