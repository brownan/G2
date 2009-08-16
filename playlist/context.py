# -*- coding: utf-8 -*-

from pydj.playlist.utils import listenerCount

def listenersContextProcessor(request):
  return {'listeners': listenerCount()}