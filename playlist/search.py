# -*- coding: utf-8 -*-

from Plex import *
from django.db.models import Q
from pydj.playlist.models import Song
import StringIO

class Search:
  
  def __init__(self, query):
    self.actions = {"artist": "artist__name",
                    "album": "album__name",
                    "title": "title",
                    }
    self.modifiers = {"=": "__iexact",
                      ":": "__icontains"}
    
    tokens = [Str(token) for token in self.actions.keys()] 
    self.lexicon = Lexicon([(Alt(*tokens), "token"),
                            (Rep1(AnyBut(" ")), "term"),
                            (Rep1(Any(" \t\n")), IGNORE)])
    
    self.query = query
    
  def _parseString(self, query=None):
    """Return a parsed tuple list representing query"""
    if query is None:
      query = self.query
    input = StringIO.StringIO()
    input.write(query)
    input.seek(0) #pretend query is a file
    s = Scanner(self.lexicon, input)
    last = s.read()
    tuples = []
    while last[0]: #read up till final None
      print last
      if last[0] == "term":
        last = self._parseTerm(last)
      else:
        last = [last] #to make extend()) call work
      tuples.extend(last)
      last = s.read()
    return tuples
  
  def _parseTerm(self, (type, arg)):
    """Find modifiers (and actions) in a term tuple, and appropriately parses them
    
    Return tuple list suitable for extension onto parsing results"""
    
    for modifier in self.modifiers.keys():
      if arg.find(modifier) > -1:
        term = list(arg.partition(modifier))
        return  self._parsePartitionedTerm(term)
      
    return [(type, arg)]
        
  def _parsePartitionedTerm(self, term):
    """Convert a term that has been partitioned by parseTerm into a nice list"""
    #work backwards as we may be deleting elements which would muck things up otehrwise
    if len(term[2]) == 0:
      del term[2]
    else:
      term[2] = ('term', term[2])
    term[1] = ('modifier', term[1]) #assume we've been given valid input
    if len(term[0]) == 0:
      del term[0]
    elif term[0] in self.actions.keys():
      term[0] = ("token", term[0])
    else:
      term[0] = ("term", term[0]) 
    return term
        
  
  def _makeQuery(self, tuples):
    """Returns a list of queries ready to be used like so: Song.objects.filter(**query)"""
    queries = [] #list of argument name, argument tuples for filter
    action = "title__icontains" #default action
    term = []
    print tuples
    for i, (type, arg) in enumerate(tuples):
      if type == "term":
        term.append(arg) #part of a search string
      elif type == "token":
        try:
          next = tuples[i+1]
        except IndexError:
          term.append(arg) #action is meant as a term
          continue
        
        if next[0] == 'modifier': #check whether next tuple is modifier
          if len(term):
            queries.append((action, " ".join(term))) #sort out last search term
          action = self.actions[arg] + self.modifiers[next[1]]
          modifier_handled = True #tell next iteration to ignore modifier
          term = [] #empty search terms list
        else: #not to be treated as token
          term.append(arg)
           
        
      elif type == "modifier":
        if modifier_handled: #handled already: ignore (but reset flag)
          modifier_handled = False
        else: #just normal term
          term.append(arg) 
    if term: #still got some clearing up to do
      queries.append((action, " ".join(term)))
    
    #convert to dict for passing to filter()
    dict = {}
    dict.update(queries)
    return dict 
  
  def getResults(self):
    query = self._makeQuery(self._parseString())
    return Song.objects.select_related().filter(**query)
      
    
if __name__ == "__main__":
  s = Search("title = electioneering")
  print s._makeQuery(s._parseString())
  print s.getResults()

  
