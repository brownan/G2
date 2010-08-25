# -*- coding: utf-8 -*-

from playlist.utils import gbsfmListenerCount, ghettoListenerCount
from playlist.cue import CueFile
from playlist.models import PlaylistEntry, Rating, SongReport, SongEdit

from django.db import connection
from django.conf import settings

def listenersContextProcessor(request):
  if not request.user.is_authenticated(): return {}
  return {
    'gbsfm_listeners': gbsfmListenerCount(),
    'ghetto_listeners': ghettoListenerCount()
  }
  
def newReportsContextProcessor(request):
  if not request.user.has_perm('playlist.approve_reports'): return {}
  
  if SongReport.objects.filter(approved=False, denied=False):
    return {'new_reports': True}
  else:
    return {'new_reports': False}
  
def newEditsContextProcessor(request):
  if not request.user.has_perm("playlist.view_edits"): return {}
  
  if SongEdit.objects.filter(applied=False, denied=False):
    return {'new_edits': True}
  else:
    return {'new_edits': False}
  
def positionContextProcessor(request):
  if not request.user.is_authenticated(): return {}
  cue = CueFile(settings.LOGIC_DIR + "/ices.cue")
  d = {}
  try:
    now_playing = PlaylistEntry.objects.nowPlaying().song
  except PlaylistEntry.DoesNotExist:
    d['song_position'] = d['song_progress'] = d['song_length'] = 0
  else:
    d['song_position'] = cue.getTime(now_playing)
    d['song_progress'] = cue.getProgress()*100 #percentagise
    d['song_length'] = now_playing.length
  return d
  
def commentProcessor(request):
  if not request.user.is_authenticated(): return {}
  try:
    now_playing = PlaylistEntry.objects.nowPlaying().song
  except PlaylistEntry.DoesNotExist:
    return []
  comments = []
  last_comment = 0
  for comment in now_playing.comments.all().order_by("-datetime"):
    html_title = "Made on %s" % comment.datetime.strftime("%d %b %Y")
    details = {
      'body': comment.text, 
      'time': comment.datetime.strftime("%H:%M"),
      'html_title': html_title,
      'commenter': comment.user.username
    }
    last_comment = max((last_comment, comment.id))
    comments.append(details)
  
  return {'curr_comments': comments, 'last_comment': last_comment}
  
def nowPlayingContextProcessor(request):
  if not request.user.is_authenticated(): return {}
  try:
    now_playing = PlaylistEntry.objects.nowPlaying().song
    try:
      user_vote =  int(now_playing.ratings.get(user=request.user).score)
    except Rating.DoesNotExist:
      user_vote = 0
    return {
      'now_playing': now_playing, 
      'user_vote': user_vote,
      'accuracy': 1 #for average score
    }
  except PlaylistEntry.DoesNotExist:
    return {}  #fun fallback to avoid errors
  
    
  
  
def SQLLogContextProcessor(request):

  time = 0.0
  for q in connection.queries:
    time += float(q['time'])
  show_queries = settings.SHOW_QUERIES
  return {'sqllog':connection.queries,'sqlcount':len(connection.queries),'sqltime':time, 'show_queries':show_queries}


