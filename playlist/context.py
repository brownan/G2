# -*- coding: utf-8 -*-

from pydj.playlist.utils import listenerCount
from django.db import connection
from django.conf import settings

def listenersContextProcessor(request):
  return {'listeners': listenerCount()}
  
  
def SQLLogContextProcessor(request):

  time = 0.0
  for q in connection.queries:
    time += float(q['time'])
  show_queries = settings.SHOW_QUERIES
  return {'sqllog':connection.queries,'sqlcount':len(connection.queries),'sqltime':time, 'show_queries':show_queries}


