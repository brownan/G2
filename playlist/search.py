# -*- coding: utf-8 -*-

from Plex import *
from django.db.models import Q
from pydj.playlist.models import Song
import StringIO

class Search:
  
  def __init__(self, query):
    self.actions = {"artist:": lambda s: Q(artist__name__icontains=s),
                    "album:": lambda s: Q(album__name__icontains=s),
                    "title:": lambda s: Q(title__icontains=s),
                    }
    tokens = [Str(token) for token in self.actions.keys()] 
    self.lexicon = Lexicon([(Alt(*tokens), "token"),
                            (Rep1(AnyBut(" ")), "term"),
                            (Rep1(Any(" \t\n")), IGNORE)])
    
    self.query = query
    
  def _parseString(self, query=None):
    """Returns a parsed tuple list representing query"""
    if query is None:
      query = self.query
    input = StringIO.StringIO()
    input.write(query)
    input.seek(0) #pretend query is a file
    s = Scanner(self.lexicon, input)
    last = s.read()
    tuples = []
    while last[0]: #read up till final None
      tuples.append(last)
      last = s.read()
    return tuples
  
  def _makeQuery(self, tuples):
    """Returns a list of queries ready to be used like so: Song.objects.filter(*query)"""
    queries = []
    start = 0
    action = lambda s: Q(title__icontains=s)
    term = []
    for type, arg in tuples:
      if type == "term":
        term.append(arg) #part of a search string
      elif type == "token":
        queries.append(action(" ".join(term))) #sort out last search term
        action = self.actions[arg] #set up stuff to be done to next lot of terms
        term = [] #empty search terms list
    if term: #still got some clearing up to do
      queries.append(action(" ".join(term)))
      
    return queries
  
  def getResults(self):
    query = self._makeQuery(self._parseString())
    return Song.objects.select_related().filter(*query)
      
    
if __name__ == "__main__":
  s = Search("electioneering artist: radiohead")
  print s.getResults()
  
