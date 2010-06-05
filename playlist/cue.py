# -*- coding: utf-8 -*-

class CueFile:
  
  def __init__(self, path=None):
    if path is None:
      pass #TODO get path from settings
      
    try:
      self._file = open(path)
    except IOError:
      pass
    
  def _getLine(self, line):
    """Return the contents of the line specified and go back to the start of the file"""
    try:
      line = self._file.readlines()[line]
      self._file.seek(0)
    except (AttributeError, IndexError):
      line = "0"
    return line
    
  def getProgress(self):
    """Return the position in the song as a number between 0 and 1"""
    return float(self._getLine(4))/100
    
  def getTime(self, song):
    """Given a Song object, return the position, in seconds, that song is at
    
    Assumes the song is playing."""
    
    return song.length * self.getProgress()
