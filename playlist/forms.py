# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.contrib.auth.forms import UserCreationForm

from playlist.utils import getObj
from playlist.models import *

class StringObjectField(forms.CharField):
  """Converts a string to the appropriate (presumably artist/album) object"""
  
  def __init__(self, model, *args, **kwargs):
    self.model = model
    forms.CharField.__init__(self, *args, **kwargs)
    
  def to_python(self, value):
    value = super(forms.CharField, self).to_python(value)
    return getObj(self.model, value)
    
  def clean(self, value):
    if not isinstance(value, self.model):
      return getObj(self.model, value)
    return value
    
class SongIDField(forms.CharField):
  """Converts a song ID to a song instance, raising a ValidationError if it doesn't exist."""
  
  def __init__(self, *args, **kwargs):
    forms.CharField.__init__(self, *args, **kwargs)
  
  def to_python(self, value):
    value = super(forms.CharField, self).to_python(value)
    try:
      value = int(value)
    except ValueError:
      raise forms.ValidationError, "The duplicate ID must be numeric"
    try:
      song = Song.objects.get(id=value)
    except Song.DoesNotExist:
      raise forms.ValidationError, "The given duplicate ID is invalid!"
    return song
  
  def clean(self, value):
    if value == 0 or value == "":
      return None
    if isinstance(value, Song):
      return value
    try:
      value = int(value)
    except ValueError:
      raise forms.ValidationError, "The duplicate ID must be numeric"
    try:
      song = Song.objects.get(id=value)
    except Song.DoesNotExist:
      raise forms.ValidationError, "The given duplicate ID is invalid!"
    
    return song
  

class UploadFileForm(forms.Form):
  file  = forms.FileField()

class SearchForm(forms.Form):
  query = forms.CharField(max_length=100)
  orphan = forms.BooleanField(required=False, initial=False)
  
  def clean_query(self):
    if len(self.cleaned_data['query']) < 3:
      raise forms.ValidationError, "Query should be 3 characters long or more."
    return self.cleaned_data['query']
  
class SongForm(forms.ModelForm):
  
  #def __init__(self, *args, **kwargs):
    ##self.artist.inital = kwargs['instance'].artist.name
    ##self.album.inital = kwargs['instance'].album.name
    #super(forms.ModelForm, self).__init__(self, *args, **kwargs)
    

  artist = StringObjectField(Artist, max_length=300) #replace dropdowns with charfields
  album = StringObjectField(Album, max_length=300) #they should be filled in the template 
  class Meta:
    model = Song
    
  
  #def clean_artist(self):
     ##convert strings to objects
    #self.cleaned_data['artist'] = getObj(Artist, self.cleaned_data['artist'])
    #self.cleaned_data['album'] = getObj(Album, self.cleaned_data['album'])
    #print super(MyModelFormSet, self).clean()
    #return cleaned_data

class SettingsForm(forms.ModelForm):
  class Meta:
    #model = UserProfile
    fields = ()
    
#class SearchForm(forms.Form):
 # pass
    
class CommentForm(forms.Form):
  comment = forms.CharField(max_length=400)
  
class BanForm(forms.Form):
  reason = forms.CharField(max_length=100)
  
class RegisterForm(UserCreationForm):
  passcode = forms.CharField(max_length=50)
  
class ReportForm(forms.ModelForm):
  duplicate = SongIDField(required=False)
  
  class Meta:
    model = SongReport
    fields = ['corrupt', 'is_duplicate', 'duplicate', 'not_music', 'other', 'user_note']

  
class NewRegisterForm(forms.Form):
  saname = forms.CharField(max_length=30, label="SA Username:")
  password1 = forms.CharField(max_length=30, label="Desired Password:", widget=forms.PasswordInput)
  password2 = forms.CharField(max_length=30, label="Confirm Password:", widget=forms.PasswordInput)
  email = forms.EmailField(label="E-mail Address:")
  randcode = forms.CharField(max_length=32, widget=forms.HiddenInput)
      
  def clean(self):
    if self.cleaned_data['password1'] != self.cleaned_data['password2']:
      raise forms.ValidationError, "Passwords must match"
    if len(self.cleaned_data['password1']) < 4:
      raise forms.ValidationError, "Password too short: must be at least 4 characters"
    
    return self.cleaned_data
  
  def clean_saname(self):
    try:
      User.objects.get(username=self.cleaned_data['saname'])
      raise forms.ValidationError, "Username already registered. If you're not happy about this, PM Jonnty."
    except User.DoesNotExist:
      return self.cleaned_data['saname'] 
      
  
class WelcomeMsgForm(forms.Form):
  message = forms.CharField(max_length=2000, widget=forms.Textarea)
