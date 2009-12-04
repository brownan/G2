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
  now_playing = PlaylistEntry.objects.nowPlaying().song
  d['song_position'] = cue.getTime(now_playing)
  d['song_progress'] = cue.getProgress()
  d['song_length'] = now_playing.length
  return d
  
  
def SQLLogContextProcessor(request):

  time = 0.0
  for q in connection.queries:
    time += float(q['time'])
  show_queries = settings.SHOW_QUERIES
  return {'sqllog':connection.queries,'sqlcount':len(connection.queries),'sqltime':time, 'show_queries':show_queries}


