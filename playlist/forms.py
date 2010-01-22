# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.contrib.auth.forms import UserCreationForm

from playlist.utils import getObj
from playlist.models import *


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

  artist = forms.CharField(max_length=300) #replace dropdowns with charfields
  album = forms.CharField(max_length=300) #they should be filled in the template 
  class Meta:
    model = Song
    
  
  def save(self):
    self.cleaned_data['artist'] = getObj(Artist, self.cleaned_data['artist'], self.initial['artist']) #convert strings to objects
    self.cleaned_data['album'] = getObj(Album, self.cleaned_data['album'])
    forms.ModelForm.save(self)
  

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
