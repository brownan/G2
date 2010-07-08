# -*- coding: utf-8 -*-

    #######################################################################
    # This file is part of the g2 project.                                #
    #                                                                     #
    # g2 is free software: you can redistribute it and/or modify          #
    # it under the terms of the Affero General Public License, Version 1  #
    # (as published by Affero, Incorporated) but not any later            #
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
import random
from hashlib import md5
from urllib2 import URLError
from subprocess import Popen
import logging
import simplejson as json

from django.http import *
from django.template import Context, loader
from django.core.urlresolvers import reverse
from django.core.serializers import serialize
from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.shortcuts import render_to_response
import django.contrib.auth.views
import django.contrib.auth as auth
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import RequestContext
from django.template.loader import render_to_string
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Avg, Max, Min, Count, Q
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import permission_required, login_required
from django.views.generic.list_detail import object_list


from playlist.forms import *
from playlist.models import *
from playlist.utils import getSong, getObj, listenerCount
from playlist.upload import UploadedFile
from playlist.search import Search
from playlist.cue import CueFile
from playlist.pllib import Playlist
from sa import SAProfile, IDNotFoundError




permissions = ["upload_song", "view_artist", "view_playlist", "view_song", "view_user", "queue_song"]

PIDFILE = settings.LOGIC_DIR+"/pid"
SA_PREFIX = "http://forums.somethingawful.com/member.php?action=getinfo&username="
LIVE = settings.IS_LIVE
MAX_EVENTS = 20 #maximum number of events premissible for one event type


def now():
  return " ".join(datetime.datetime.now().isoformat().split("T"))

  
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
  except KeyError: 
    return HttpResponseRedirect(reverse('login'))
    
@permission_required('playlist.view_playlist')
def playlist(request, lastid=None):
  #normal entry route
  if "gbsfm.ath.cx" in request.get_host():
    return HttpResponseRedirect("/images/moved.html")
  return jsplaylist(request, lastid)
  
  
def jsplaylist(request, lastid=None):
  
  if lastid is None:
    try:
      historylength = request.user.get_profile().s_playlistHistory
    except AttributeError:
      historylength = 10
    
  aug_playlist = Playlist(request.user, historylength).fullList()
  accuracy = 1 #TODO: make accuracy user setting
  can_skip = request.user.has_perm('playlist.skip_song')
  lastremoval = RemovedEntry.objects.aggregate(Max('id'))['id__max']
  try:
    welcome_message = Settings.objects.get(key="welcome_message").value
  except:
    welcome_message = None
  
  length = PlaylistEntry.objects.length()
  
  return render_to_response('jsplaylist.html',  {'aug_playlist': aug_playlist, 'can_skip':can_skip, 
  'lastremoval':lastremoval, 'welcome_message':welcome_message, 
  'length':length, 'accuracy':accuracy}, context_instance=RequestContext(request))

  
 # return render_to_response('index.html',  {'aug_playlist': aug_playlist, 'msg':msg, 'can_skip':can_skip}, context_instance=RequestContext(request))
  

@login_required()
def ajax(request):
    events = []
    length_changed = False #True if any actions would have changed the playlist length
    
    #new removals
    last_removal = int(request.REQUEST.get('last_removal', -1))
    
    if last_removal != -1:
      removals = RemovedEntry.objects.filter(id__gt=last_removal)
      removal_events = []
      if removal_events:
        length_changed = True
      for removal in removals:
        removal_events.append(('removal', {"entryid": removal.oldid, "id": removal.id}))
      if len(removal_events) > MAX_EVENTS:
        removal_events = removal_events[:MAX_EVENTS] 
      events.extend(removal_events)
      

      
        
    #get now playing track
    client_playing = int(request.REQUEST.get('now_playing', 0))
    #always output as if this isn't given it's definitely needed 
    server_playing = PlaylistEntry.objects.nowPlaying()
    
    #check for submitted comment
    try:
      comment = request.REQUEST['comment']
    except KeyError:
      pass
    else:
      server_playing.song.comment(request.user, comment)
      #TODO: handle comment being too long gracefully
      
    #check for submitted vote
    try:
      vote = request.REQUEST['vote']
    except KeyError:
      pass
    else:
      server_playing.song.rate(vote, request.user)    
    
    if server_playing.id != client_playing:
      events.append(('now_playing', server_playing.id))
      length_changed = True
      #new title needed
      try:
        events.append(('metadata', PlaylistEntry.objects.nowPlaying().song.metadataString()))
        linkedMetadata = render_to_string('linked_metadata.html', context_instance=RequestContext(request))
        events.append(('linkedMetadata', linkedMetadata))
      except PlaylistEntry.DoesNotExist:
        pass
      #new song length needed
      events.append(('songLength', PlaylistEntry.objects.nowPlaying().song.length))
      #new comments needed
      events.append(('clearComments', ''))
      comments = server_playing.song.comments.all().order_by("datetime") #ensure oldest first - new comments are placed at top of update list
      for comment in comments:
        events.append(comment.ajaxEvent())
    else:
      try:
        last_comment = int(request.REQUEST['last_comment'])
      except (ValueError, TypeError, KeyError):
        pass
      else:
        comments = server_playing.song.comments.all().order_by("datetime").filter(id__gt=last_comment)
        for comment in comments:
          events.append(comment.ajaxEvent())
      
    #send user vote & song avg vote_count
    try:
      user_vote = server_playing.song.ratings.get(user=request.user).score
    except Rating.DoesNotExist:
      user_vote = 0
    
    if server_playing.song.voteno == 1:
      score_str = "%.1f (%d vote)" % (server_playing.song.avgscore, server_playing.song.voteno)
    elif server_playing.song.voteno > 1:
      score_str = "%.1f (%d votes)" % (server_playing.song.avgscore, server_playing.song.voteno, )
    else:
      score_str = "no votes"
    events.append(('userVote', int(user_vote)))
    events.append(('score', score_str))
    
    #new adds
    try:
      last_add = int(request.REQUEST['last_add'])
    except (ValueError, TypeError, KeyError):
      pass
    else:
      accuracy = 1 #TODO: replace with user setting
      aug_playlist = Playlist(request.user).fromLastID(last_add)
      if len(aug_playlist) > 0:
        length_changed = True
        if len(aug_playlist) > MAX_EVENTS:
          aug_playlist = aug_playlist[:MAX_EVENTS]
        html = render_to_string('playlist_table.html',  {'aug_playlist': aug_playlist, 'accuracy':accuracy},
        context_instance=RequestContext(request))
        events.append(("adds", html))   
    
    
        
    
    if length_changed:
      length = PlaylistEntry.objects.length()
      events.append(('pllength', render_to_string('pl_length.html', {'length':length})))

    #handle cuefile stuff
    tolerance = 5 #tolerance in seconds between real and recieved time TODO: replace with internal setting
    
    position = request.REQUEST.get('position', None)
    if position:
      cue = CueFile(settings.LOGIC_DIR + "/ices.cue")
      now_playing = PlaylistEntry.objects.nowPlaying().song
      if abs(int(position) - cue.getTime(now_playing)) >= tolerance: 
        events.append(('songPosition', cue.getTime(now_playing)))
    
    return HttpResponse(json.dumps(events))
  

def api(request, resource=""):
  
  #authentication
  if request.user.is_authenticated():
    user = request.user
    
    
  else: #non-persistent authentication for things like bots and clients
    try:
      username = request.REQUEST['username']
    except KeyError:
      try: #is there a userid arg?
        username = User.objects.get(id=request.REQUEST['userid']).username
      except (User.DoesNotExist, KeyError):
        return HttpResponseForbidden()
        
    try: #try using password
      password = request.REQUEST['password']
      user = authenticate(username=username, password=password)
      if user is None:
        return HttpResponseForbidden()
    except KeyError:
      try: #try api_key
        api_key = request.REQUEST['key']
        userprofile = UserProfile.objects.get(user__username=username, api_key=api_key)
        user = userprofile.user
        if not userprofile.api_key: #api key not yet set
          return HttpResponseForbidden()
      except (KeyError, User.DoesNotExist):
        return HttpResponseForbidden()
        
  if resource == "nowplaying":
    try:
      entryid = PlaylistEntry.objects.nowPlaying().id
      return HttpResponse(str(entryid))
    except PlaylistEntry.DoesNotExist:
      return HttpResponse()
    
  
  if resource == "deletions":
    try:
      lastid = request.REQUEST['lastid']
    except KeyError:
      lastid = 0
    if not lastid: lastid = 0 #in case of "&lastid="
    deletions = RemovedEntry.objects.filter(id__gt=lastid)
    data = serialize("json", deletions, fields=('oldid'))
    return HttpResponse(data)
    
  

  if resource == "adds":
    try:
      lastid = request.REQUEST['lastid']
    except KeyError:
      lastid = 0
    if not lastid: lastid = 0
    adds = PlaylistEntry.objects.extra(select={"user_vote": "SELECT ROUND(score, 0) FROM playlist_rating WHERE playlist_rating.user_id = \
    %s AND playlist_rating.song_id = playlist_playlistentry.song_id", "avg_score": "SELECT AVG(playlist_rating.score) FROM playlist_rating WHERE playlist_rating.song_id = playlist_playlistentry.song_id", "vote_count": "SELECT COUNT(*) FROM playlist_rating WHERE playlist_rating.song_id = playlist_playlistentry.song_id"},
    select_params=[request.user.id]).select_related("song__artist", "song__album", "song__uploader", "adder").order_by('addtime').filter(id__gt=lastid)
    data = serialize("json", adds, relations={'song':{'relations':('artist'), 'fields':('title', 'length', 'artist')}, 'adder':{'fields':('username')}})
    return HttpResponse(data)
    
  #if resource == "history":
    #try:
      #lastid = request.REQUEST['lastid']
    #except KeyError:
      #raise Http404
    #if not lastid: raise Http404
    #if lastid[0] != 'h':
      #raise Http404 #avert disaster
    #lastid = lastid[1:] #get rid of leading 'h'
    #history = OldPlaylistEntry.objects.select_related().filter(id__gt=lastid)
    #data = serialize("json", history, relations={'song':{'relations':('artist'), 'fields':('title', 'length', 'artist')}, 'adder':{'fields':('username')}})
    #return HttpResponse(data)
  
  if resource == "pltitle":
    try:
      return HttpResponse(PlaylistEntry.objects.nowPlaying().song.metadataString() + " - GBS-FM")
    except PlaylistEntry.DoesNotExist:
      return HtttpResponse("GBS-FM")
    
  
  def getSong(request):
    """Returns a song object given a request object"""
    try:
      songid = request.REQUEST['songid']
      songid = int(songid)
      song = Song.objects.get(id=songid)
    except KeyError:
      song = PlaylistEntry.objects.nowPlaying().song
    except ValueError:
      if songid == "curr":
        song = PlaylistEntry.objects.nowPlaying().song
      elif songid == "prev":
        song = OldPlaylistEntry.objects.select_related("song").extra(where=['playlist_oldplaylistentry.id =\
        (select max(playlist_oldplaylistentry.id) from playlist_oldplaylistentry)'])[0].song
    return song
  
  if resource == "favourite":
    song = getSong(request)
    if song in user.get_profile().favourites.all():
      state = "old favourite"
    else:
      user.get_profile().favourites.add(song)
      state = "new favourite"
    return HttpResponse(song.metadataString() +'\n' + state)
    
  if resource == "unfavourite":
    song = getSong(request)
    user.get_profile().favourites.remove(song)
    return HttpResponse(song.metadataString())
    
  #if resource == "getuser":
    #try:
      #user = User.objects.get(username=request.REQUEST['username'])
    #except KeyError:
      #user = request.user
    #except User.DoesNotExist:
      #raise Http404
    
    #return HttpResponse(user.id)
    
  if resource == "getfavourite":
    """
    Get a song from favourites of the specified user (ID: userid).
    Trys to make it addable but will return best unaddable one otherwise.
    """
    try:
      lover = User.objects.get(id=int(request.REQUEST['loverid']))
    except KeyError:
      try:
        lover = User.objects.get(username=str(request.REQUEST['lovername']))
      except KeyError:
        lover = user
    songs = lover.get_profile().favourites.all().check_playable(user)
    unplayed = songs.filter(on_playlist=False, banned=False) #TODO: use recently_played too!
    if unplayed: #only use it if there are actually unplayed songs!
      songs = unplayed
    try:
      song = random.choice(songs)
    except:
      raise Http404
    
    return HttpResponse(str(song.id) + "\n" + song.metadataString())
  
  if resource == "vote":
    try:
      vote = float(request.REQUEST['vote'])
    except KeyError:
      raise Http404
    song = getSong(request)
    prevscore = song.rate(vote, user)
    
    return HttpResponse(str(prevscore) + " " +song.metadataString())
  
  if resource == "comment":
    try:
      comment = request.REQUEST['comment']
    except KeyError:
      raise Http404
    song = getSong(request)
    time = song.comment(user, comment)
    
    return HttpResponse(str(time))
    
  if resource == "pllength":
    length = PlaylistEntry.objects.length()
    try:
      comment = request.REQUEST['formatted']
      return render_to_response('pl_length.html', {'length':length})
    except KeyError:
      return HttpResponse(str(length['seconds']) + '\n' + str(length['song_count']))
  
  if resource == "add":
    try:
      song = Song.objects.select_related().get(id=request.REQUEST['songid'])
    except (KeyError, Song.DoesNotExist):
      raise Http404
    
    try: 
      song.playlistAdd(user)
    except AddError, e:
      return HttpResponseBadRequest(e.args[0])
    
    return HttpResponse(song.metadataString())
    
  if resource == "uncomment":
    try:
      comment = Comment.objects.select_related().filter(user=user)[0]
      comment.delete()
    except IndexError:
      raise Http404
    
    return HttpResponse(comment.song.metadataString())
  
  if resource == "metadata":
    song = getSong(request)
    return HttpResponse(song.artist.name + "\n" + song.album.name + "\n" + song.title)

  if resource == "metadata2":
    song = getSong(request)
    return HttpResponse(song.artist.name + "\n" + song.album.name + "\n" + song.title + "\n" + str(song.length)) 

  if resource == "randid":
    randomid = randomdongid()
    return HttpResponse(int(randomid[0]))

  if resource == "plinfo":
    pldongid = request.GET.get('plid', 0)
    playlistinfo = plinfoq(pldongid)
    return HttpResponse(str(playlistinfo[0]) + "\n" + playlistinfo[2] + "\n" + playlistinfo[3] + "\n" + playlistinfo[1])
    #return HttpResponse(playlistinfo)
      
  if resource == "listeners":
    return HttpResponse(listenerCount())
    
  if resource == "users":
    return HttpResponse(Users.objects.all().count())
    
  if resource == "position":
    cue = CueFile(settings.LOGIC_DIR + "/ices.cue")
    d = {}
    now_playing = PlaylistEntry.objects.nowPlaying().song
    d['position'] = cue.getTime(now_playing)
    d['progress'] = cue.getProgress()
    d['length'] = now_playing.length
    return HttpResponse(json.dumps(d))  
  
  raise Http404
  
@login_required()
def favourite(request, songid=0):
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    raise Http404
  request.user.get_profile().favourites.add(song)
  request.user.message_set.create(message="Song favourited successfully")
  
  referrer = request.META.get('HTTP_REFERER', None)
  if referrer:
    return HttpResponseRedirect(referrer)
  else:
    return HttpResponseRedirect(reverse(playlist))
  
@login_required()
def unfavourite(request, songid=0):
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    raise Http404
  request.user.get_profile().favourites.remove(song)
  request.user.message_set.create(message="Song unfavourited successfully")
  
  referrer = request.META.get('HTTP_REFERER', None)
  if referrer:
    return HttpResponseRedirect(referrer)
  else:
    return HttpResponseRedirect(reverse(playlist))
  
  
@login_required()
def user_settings(request):
  profile = request.user.get_profile()
  if not profile.api_key:
    keygen(request)
  api_key = profile.api_key
  
  if request.method == "POST":
    password_form = PasswordChangeForm(request.user, request.POST)
    if password_form.is_valid():
      password_form.save() #resets password appropriately
      request.user.message_set.create(message="Password changed sucessfully")
  else:
    password_form = PasswordChangeForm(request.user)
      
  return render_to_response('user_settings.html', {'api_key': api_key, 'password_form': password_form}, context_instance=RequestContext(request))
  
@login_required()
def keygen(request):
  """Generates an API key which can be used instead of a password for API calls but not for important things like deletes. Checks for dupes."""
  while True:
    #keep generating keys until we get a unique one
    newquay = lambda: md5(settings.SECRET_KEY + str(getrandbits(64)) + request.user.username).hexdigest()
    key = newquay()
    try:
      UserProfile.objects.get(api_key=key)
    except UserProfile.DoesNotExist:
     break
  profile = request.user.get_profile()
  profile.api_key = key
  profile.save()
  return HttpResponseRedirect(reverse('user_settings')) 

@login_required()
def removeentry(request, entryid):
  try:
    entry = PlaylistEntry.objects.select_related().get(id=entryid)
  except PlaylistEntry.DoesNotExist:
    raise Http404
  if ((entry.adder == request.user) or request.user.has_perm("playlist.remove_entry")) and not entry.playing:
    logging.info("User %s (uid %d) removed songid %d from playlist at %s" % (request.user.username, request.user.id, entry.song.id, now()))
    entry.remove()
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

@permission_required('playlist.merge_song')
def merge_song(request, mergeeid, mergerid):
  """
  Merge song merger into mergee, resulting in the destruction of song merger
  """
  try:
    merger = Song.objects.get(id=mergerid)
    mergee = Song.objects.get(id=mergeeid)
  except Song.DoesNotExist:
    raise Http404
  
  logging.info("Mod %s (uid %d) merged song with sha_hash %s into %d at %s" %
    (request.user.username, request.user.id, merger.sha_hash, mergee.id, now()))
    
  mergee.merge(merger)
  request.user.message_set.create(message="Song merged in successfully")

  return HttpResponseRedirect(reverse('song', args=[mergee.id]))

@permission_required('playlist.view_song')
def song(request, songid=0, edit=None):
  try:
    song = Song.objects.select_related("uploader", "artist", "album", "location").get(id=songid)
  except Song.DoesNotExist:
    raise Http404 # render_to_response('song.html', {'error': 'Song not found.'})
    
  editform = SongForm(request.POST, instance=song)
  if editform.is_valid():
    if request.method == "POST" and (request.user.has_perm('playlist.edit_song') or (request.user == song.uploader)):
      #user has correct permissions to edit song 
      editform.save()
      logging.info("User/mod %s (uid %d) edited songid %d at %s" % (request.user.username, request.user.id, song.id, now()))
    else:
      #queue a SongEdit
      #MUST CHANGE IF TAGS CHANGE (sorry code nazis)
      edit = SongEdit()
      for field in ["title", "composer", "lyricist", "remixer", "genre", "track"]:
        if getattr(editform, field) != getattr(editform.instance, field):
          FieldEdit(field=field, new_value=getattr(editform, field), song_edit=edit).save()
      if editform.instance.artist.name != editform.artist.name:
        FieldEdit(field=field, new_value=editform.artist.name, song_edit=edit).save()
      if editform.instance.artist.name != editform.artist.name:
        FieldEdit(field=field, new_value=editform.artist.name, song_edit=edit).save()
      edit.requester = request.user
      edit.save()
      request.user.message_set.create(message="Your edit has been queued for mod approval.")
  else:
    editform = SongForm(instance=song)
    
  commentform = CommentForm()
  comments = Comment.objects.select_related().filter(song=song)
  banform = BanForm()
  can_ban = request.user.has_perm('playlist.ban_song')
  if request.user.get_profile().canDelete(song):
    can_delete = True
  else:
    can_delete = False

  try:
    vote = Rating.objects.get(user=request.user, song=song).score
  except Rating.DoesNotExist:
    vote = 0
  if request.user.has_perm('playlist.edit_song') or request.user.has_perm('playlist.download_song'):
    path = song.getPath()
  else:
    path = None
    
  favourite = song in request.user.get_profile().favourites.all()
  is_orphan = (song.uploader == User.objects.get(username="Fagin"))
    
    
  return render_to_response('song.html', \
  {'song': song, 'editform':editform, 'edit':edit,'commentform':commentform, 
  'currentuser':request.user, 'comments':comments, 'can_ban':can_ban, 'is_orphan':is_orphan, 
  'banform':banform, 'can_delete':can_delete, 'can_edit':can_edit, 'vote':vote, 'path':path, 
  'favourite' : favourite}, \
  context_instance=RequestContext(request))

@permission_required("playlist.download_song")
def download_song(request, songid):
  try:
    song = Song.objects.get(id=songid)
  except:
    raise Http404
  
  response = HttpResponse(mimetype="audio/mpeg")
  try:
    response['Content-Disposition'] = 'attachment; filename="' + song.title + "." + song.format + '"'
  except UnicodeEncodeError:
    #don't bother working around, just use the hash
    response['Content-Disposition'] = 'attachment; filename="' + song.sha_hash + "." + song.format + '"'
  response['X-Sendfile'] = song.getPath()
  return response

@login_required()
def album(request, albumid=None):
  try:
    album = Album.objects.select_related().get(id=albumid)
  except Album.DoesNotExist:
    raise Http404
  songs = album.songs.all().check_playable(request.user).select_related().order_by('track')
  return render_to_response('album.html', {'album': album, 'songs': songs}, context_instance=RequestContext(request))
  
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
def deletesong(request, songid=0, confirm=None):
  """Deletes song with songid from db. Does not yet delete file."""
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    raise Http404
  
  if confirm != "yes":
    return render_to_response("delete_confirm.html", {'song': song}, context_instance=RequestContext(request))

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
  try:
    owner=  User.objects.get(id=userid)
  except User.DoesNotExist:
    raise Http404
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
  
@login_required()
def delete_comment(request, commentid):
  try:
    comment = Comment.objects.get(id=commentid)
  except:
    raise Http404
  if request.user.has_perm("playlist.delete_comment") or request.user == comment.user:
    comment.delete()
    request.user.message_set.create(message="Comment deleted successfully")
  else:
    request.user.message_set.create(message="You don't have permission to delete this comment")
  return HttpResponseRedirect(reverse('song', args=[comment.song.id]))

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
  try:
    artist = Artist.objects.get(id=artistid)
  except Artist.DoesNotExist:
    raise Http404
  print artist
  songs = Song.objects.select_related("artist", "album").check_playable(request.user).filter(artist=artist).order_by("album__name", "track")
  print songs
  return render_to_response("artist.html", {'songs': songs, 'artist': artist}, context_instance=RequestContext(request))
    
@permission_required('playlist.queue_song')
def add(request, songid=0): 
  try:
    try:
      song = Song.objects.get(id=songid)
    except Song.DoesNotExist:
      raise Http404
    song.playlistAdd(request.user)
  except AddError, e:
    msg = "Error: %s" % (e.args[0])
    request.user.message_set.create(message=msg)
    return HttpResponseRedirect(reverse("playlist"))      

  if song.isOrphan(): 
    song.uploader = request.user
    song.save()
    msg = "This dong was an orphan, so you have automatically adopted it. Take good care of it!"
    request.user.message_set.create(message=msg)
    
  request.user.message_set.create(message="Track added successfully!")

  return HttpResponseRedirect(reverse("playlist"))
  
def next(request, authid):
  if authid == settings.NEXT_PASSWORD:
    try:
      entry = PlaylistEntry.objects.nowPlaying().next()
      location = getSong(entry.song)
      metadata = u"%s [blame %s]" % (entry.song.metadataString(request.user), entry.adder.username)
      return HttpResponse(location +'\n'+ metadata)
    except PlaylistEntry.DoesNotExist:
      pass
  return HttpResponse()
   
def newregister(request):
  get_authcode = lambda randcode: md5(settings.SECRET_KEY + randcode).hexdigest()
  get_randcode = lambda: md5(str(getrandbits(64))).hexdigest()
  error = ""
  if request.method == "POST":
    
    form = NewRegisterForm(request.POST)


    if form.is_valid():
      username = form.cleaned_data['saname']
      password = form.cleaned_data['password1']
      email = form.cleaned_data['email']
      authcode = get_authcode(form.cleaned_data['randcode'])
      error = None
      randcode = form.cleaned_data['randcode']
      
      try:
        profile = SAProfile(username)  
      except URLError:
        error = "Couldn't find your profile. Check you haven't made a typo and that SA isn't down."
      
      if LIVE:

        try:
          if len(UserProfile.objects.filter(sa_id=profile.get_id())) > 0:
            error = "You appear to have already registered with this SA account"
        except IDNotFoundError:
          error = "Your SA ID could not be found. Please contact Jonnty"
        
        if not profile.has_authcode(authcode):
          error = "Verification code not found on your profile."
        
      if len(User.objects.filter(username__iexact=username)):  
        error = "This username has already been taken. Please contact Jonnty to get a different one."
         
        
      if error is None:
        user = User.objects.create_user(username=username, email=email, password=password)
        try: g = Group.objects.get(name="Listener")
        except Group.DoesNotExist:
          g = Group(name="Listener")
          g.save()
          [g.permissions.add(Permission.objects.get(codename=s)) for s in permissions]
          g.save()
        user.groups.add(g)
        user.save()
        up = UserProfile(user=user)
        up.sa_id = profile.get_id()
        up.save()
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
  if request.method == 'GET' and "query" in request.GET: # If the form has been submitted...
    form = SearchForm(request.GET) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      query = form.cleaned_data['query']
      
      artists = Artist.objects.select_related().filter(name__icontains=query).order_by('name')
      songs = Search(query).getResults().check_playable(request.user).order_by('title')
      albums = Album.objects.select_related().filter(name__icontains=query).order_by('name')
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
        
      paginator = Paginator(songs, 100) 
      try: #sanity check
        page = int(request.GET.get('page', '1'))
      except ValueError:
        page = 1
        
      try: #range check
        songs = paginator.page(page)
      except (EmptyPage, InvalidPage):
        songs = paginator.page(paginator.num_pages)

        
      return render_to_response('search.html', {'form':form, 'artists':list(artists), 'albums':list(albums), 'songs':songs, 'query':query},\
      context_instance=RequestContext(request))
      
  else:
    form = SearchForm()
  return render_to_response('search.html', {'form':form}, context_instance=RequestContext(request))


#def info(request):
  #song = PlaylistEntry.objects.get(playing=True)
  #return HttpResponse()

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
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    raise Http404
  scuttle = User.objects.get(username="Fagin")
  if not song in Song.objects.filter(uploader=scuttle):
    request.user.message_set.create(message="You may not adopt this dong.")
    return HttpResponseRedirect(reverse("song", args=[songid]))
  else:
    song.uploader = request.user
    song.save()
    request.user.message_set.create(message="Dong adopted successfully. Take good care of it!")
    return HttpResponseRedirect(reverse("song", args=[songid]))    
