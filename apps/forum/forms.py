# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext as _
from forum.models import Post

class CreateThreadForm(forms.Form):
    title = forms.CharField(label=_("Title"), max_length=100, widget=forms.TextInput(attrs={'size': '70'}))
    body = forms.CharField(label=_("Body"), widget=forms.Textarea(attrs={'rows':16, 'cols':101}))
    subscribe = forms.BooleanField(label=_("Subscribe via email"), required=False)

class ReplyForm(forms.Form):
    body = forms.CharField(label=_("Body"), widget=forms.Textarea(attrs={'rows':16, 'cols':100}))
    subscribe = forms.BooleanField(label=_("Subscribe via email"), required=False)

class EditForm(forms.ModelForm):
  body = forms.CharField(widget=forms.Textarea(attrs={'rows':8, 'style': "width: 100%;"}))
  class Meta:
    model = Post
    fields = ["body"]
    
