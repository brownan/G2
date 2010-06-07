# -*- coding: utf-8 -*-

from playlist.utils import listenerCount
from playlist.cue import CueFile
from playlist.models import PlaylistEntry

from django.db import connection
from django.conf import settings

def listenersContextProcessor(request):
  return {'listeners': listenerCount()}
  
def positionContextProcessor(request):
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
  try:
    now_playing = PlaylistEntry.objects.nowPlaying().song
  except PlaylistEntry.DoesNotExist:
    return []
  comments = []
  last_comment = 0
  for comment in now_playing.comments.all():
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
  try:
    return {'now_playing': PlaylistEntry.objects.nowPlaying().song}
  except PlaylistEntry.DoesNotExist:
    return {'now_playing': Song.objects.all()[0]} #fun fallback to avoid errors
  
  
def SQLLogContextProcessor(request):

  time = 0.0
  for q in connection.queries:
    time += float(q['time'])
  show_queries = settings.SHOW_QUERIES
  return {'sqllog':connection.queries,'sqlcount':len(connection.queries),'sqltime':time, 'show_queries':show_queries}


