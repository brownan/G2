# -*- coding: utf-8 -*-
from django.http import HttpResponse,  HttpResponseRedirect
from django.template import Context, loader
from django.core.urlresolvers import reverse
from pydj.playlist.models import *
from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render_to_response
from utils import getSong
import django.contrib.auth.views
import django.contrib.auth as auth
from django.forms.models import modelformset_factory
import itertools


permissions = ["upload_song", "view_artist", "view_playlist", "view_song", "view_user", "queue_song", "ban_song"]


from django.contrib.auth.decorators import permission_required, login_required

class UploadFileForm(forms.Form):
  file  = forms.FileField()

class SearchForm(forms.Form):
  query = forms.CharField(max_length=100)
  
class SongForm(forms.ModelForm):

  artist = forms.CharField(max_length=300) #replace dropdowns with charfields
  album = forms.CharField(max_length=300) #they should be filled in the template 
  class Meta:
    model = Song
    #exclude = ("album", "artist")
    
  def populate(self, song):pass
    #self.artist = forms.CharField(max_length=300, initial=song.artist.name)
    #self.album = forms.CharField(max_length=300, initial=song.album.name)
  
  def save(self):
    self.cleaned_data['artist'] = Artist.objects.get_or_create(name=self.cleaned_data['artist'])[0] #convert strings to objects
    self.cleaned_data['album'] = Album.objects.get_or_create(name=self.cleaned_data['album'])[0]
    forms.ModelForm.save(self)
  

class SettingsForm(forms.ModelForm):
  class Meta:
    #model = UserProfile
    fields = ()
    
class CommentForm(forms.Form):
  comment = forms.CharField(max_length=400)
  
class BanForm(forms.Form):
  reason = forms.CharField(max_length=100)
  

@permission_required('playlist.view_playlist')
def playlist(request, msg=""):
  historylength = request.user.get_profile().s_playlistHistory
  #historylength = 10
  oldentries = OldPlaylistEntry.objects.all()
  if historylength <= oldentries.count():
    playlist = list(oldentries[oldentries.count()-historylength:]) + list(PlaylistEntry.objects.all().order_by('addtime'))
  else:
    playlist = list(oldentries) + list(PlaylistEntry.objects.all().order_by('addtime'))
  return render_to_response('playlist/index.html',  {'playlist': playlist, 'msg':msg})

@permission_required('playlist.view_song')
def song(request, songid=0, edit=None):
  try:
    song = Song.objects.get(id=songid)
  except Song.DoesNotExist:
    return render_to_response('playlist/song.html', {'error': 'Song not found.'})
  if request.method == "POST":
    editform = SongForm(request.POST, instance=song)
    if editform.is_valid():
      editform.save()
  else:
    editform = SongForm(instance=song)
  commentform = CommentForm()
  comments = Comment.objects.filter(song=song)
  banform = BanForm()
  can_ban = request.user.has_perm('playlist.ban_song')
  
  return render_to_response('playlist/song.html', \
  {'song': song, 'editform':editform, 'edit':edit,'commentform':commentform, \
  'currentuser':request.user, 'comments':comments, 'can_ban':can_ban, \
  'banform':banform})
  
@permission_required('playlist.ban_song')
def bansong(request, songid=0):
  if request.method == "POST":
    form = BanForm(request.POST)
    if form.is_valid():
      print 11
      song = Song.objects.get(id=songid)
      reason = form.cleaned_data['reason']
      print reason
      song.ban(reason)
      song.save()
      print 22
  return HttpResponseRedirect(reverse('song', args=[songid]))

@permission_required('playlist.ban_song')
def unbansong(request, songid=0, plays=0):
  song = Song.objects.get(id=songid)
  song.unban(plays)
  return HttpResponseRedirect(reverse('song', args=[songid]))
  
@login_required()
def user(request, userid):
  pass

@login_required()
def comment(request, songid): 
  song = Song.objects.get(id=songid)
  if request.method == "POST":
    form = CommentForm(request.POST)
    if form.is_valid():
      #TODO: include song time
      song.comment(request.user, form.cleaned_data['comment'])
  return HttpResponseRedirect(reverse('song', args=[songid]))


@login_required()
def rate(request, songid, vote):
  song = Song.objects.get(id=songid)
  song.rate(vote, request.user)
  return render_to_response('playlist/song.html', {'song': song})  

@permission_required('playlist.upload_song')
def upload(request):
  print request.method
  if request.method == "POST":
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      try:
        request.user.get_profile().addSong(request.FILES['file'])
      except UserProfile.DoesNotExist:
        p = UserProfile(user=request.user)
        p.save()
        request.user.get_profile().addSong(request.FILES['file'])
      except DuplicateError:
          return render_to_response('playlist/upload.html', {'form': form, 'message': "Track already uploaded"})
          
      return render_to_response('playlist/upload.html', {'form': form, 'message': "Uploaded file successfully!"})
  else:
    form = UploadFileForm()
  return render_to_response('playlist/upload.html', {'form': form, 'message': None})


@permission_required('playlist.view_artist')
def artist(request, artistid=None):
  artist = Artist.objects.get(id=artistid)
  songs = Song.objects.filter(artist=artist).order_by("album")
  return render_to_response("playlist/artist.html", {'songs': songs, 'artist': artist} )
    
@permission_required('playlist.queue_song')
def add(request, songid=0): 
  try:
    Song.objects.get(id=songid).playlistAdd(request.user)
  except AddError, e:
    return playlist(request, msg="Error: " + e.args[0])        
  return playlist(request, msg="Track successfully added!")
  
def next(request, authid):
  if authid == "777":
    try:
      entry = PlaylistEntry.objects.get(playing=True).next()
      location = getSong(entry.song)
      metadata = "%s [blame %s]" % (entry.song.metadataString(request.user), entry.adder.username)
      print 1
      return HttpResponse(location +'\n'+ metadata)
    except PlaylistEntry.DoesNotExist:
      pass
  return HttpResponse()

def register(request):
  if request.method == "POST":
    form = UserCreationForm(request.POST, request.FILES)
    if form.is_valid():
      username = form.cleaned_data['username']
      password = form.cleaned_data['password1']
      user = User.objects.create_user(username=username, email="", password=password)
      try: g = Group.objects.get(name="user")
      except Group.DoesNotExist:
        g = Group(name="user")
        g.save()
        [g.permissions.add(Permission.objects.get(codename=s)) for s in permissions]
        g.save()
      user.groups.add(g)
      user.save()
      UserProfile(user=user).save()
      return HttpResponseRedirect(reverse(django.contrib.auth.views.login))
  else:
    form = UserCreationForm()
    error = "Fill in the form properly"
  return render_to_response('playlist/register.html', {'form': form})
  
@login_required()
def search(request):
  if request.method == 'POST': # If the form has been submitted...
    form = SearchForm(request.POST) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      query = form.cleaned_data['query']
      
      artists = Artist.objects.filter(name__icontains=query).order_by('name')
      songs = Song.objects.filter(title__icontains=query).order_by('title')
      return render_to_response('playlist/search.html', {'form':form, 'artists':list(artists), 'songs':songs, 'query':query})
  else:
    form = SearchForm()
  return render_to_response('playlist/search.html', {'form':form})


def info(request):
  song = PlaylistEntry.objects.get(playing=True)
  return HttpResponse()
