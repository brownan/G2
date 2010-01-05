# -*- coding: utf-8 -*-

import itertools

from playlist.models import PlaylistEntry, OldPlaylistEntry


class Playlist(object):
  
  def __init__(self, user, history_length=0):
    """Playlist wrapper, used for accessing playlist entries in novel and interesting ways
    
    history is the number of old playlist entries to include
    user is user object for augmentation
    """
    self.history_length = history_length
    self.user = user
    self._genEntries()
    
    
  def _augment(self, entries):
    """Augment the entries so that they can be happily used in the playlist template"""
    
    aug_entries= []
    for entry in entries:
      if isinstance(entry, PlaylistEntry) and not entry.playing and (self.user.has_perm('remove_entry') or self.user == entry.adder):
        aug_entries.append({'can_remove':True, 'object':entry, 'pl':True})
      elif isinstance(entry, PlaylistEntry):
        aug_entries.append({'can_remove':False, 'object':entry, 'pl':True})
      else:
        aug_entries.append({'can_remove':False, 'object':entry, 'pl':False})
    return aug_entries
        
  def _genEntries(self):
    """Generate the entries lists oldentries and newentries"""
    
    if self.history_length <= 0:
      oldentries = []
    else:
      oldentries = OldPlaylistEntry.objects.all()
      oldentries = oldentries.extra(
      where=['playlist_oldplaylistentry.id > (select max(id) from playlist_oldplaylistentry)-%s'], 
      params=[self.history_length], 
      select={
      "user_vote": "SELECT ROUND(score, 0) FROM playlist_rating WHERE playlist_rating.user_id = %s AND playlist_rating.song_id = playlist_oldplaylistentry.song_id", 
      "avg_score": "SELECT AVG(playlist_rating.score) FROM playlist_rating \
      WHERE playlist_rating.song_id = playlist_oldplaylistentry.song_id", 
      "vote_count": "SELECT COUNT(*) FROM playlist_rating \
      WHERE playlist_rating.song_id = playlist_oldplaylistentry.song_id"
      },
      select_params=[self.user.id]).select_related()
    self.oldentries = oldentries
    
    self.newentries = PlaylistEntry.objects.extra(
    select={
      "user_vote": "SELECT ROUND(score, 0) FROM playlist_rating \
                    WHERE playlist_rating.user_id = %s \
                    AND playlist_rating.song_id \
                    = playlist_playlistentry.song_id", 
      "avg_score": "SELECT AVG(playlist_rating.score) FROM playlist_rating \
                    WHERE playlist_rating.song_id = \
                    playlist_playlistentry.song_id", 
      "vote_count": "SELECT COUNT(*) FROM playlist_rating \
                     WHERE playlist_rating.song_id = \
                     playlist_playlistentry.song_id"
    },
    select_params=[self.user.id]).select_related("song__artist", "song__album", "song__uploader", "adder").order_by('addtime')

    
    

 
    
      
  def fromLastID(self, entryid):
    """Return augmented playlist entries with ID > entryid"""
    return self._augment(self.newentries.filter(id__gt=entryid))
    
  def fullList(self):
    """Return full augmented playlist from earlest old playlist entry 
    to newest addition"""
    
    return self._augment(itertools.chain(self.oldentries, self.newentries))
