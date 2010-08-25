# -*- coding: utf-8 -*-
from pydj.playlist.models import *
from django.contrib import admin

class ArtistAdmin(admin.ModelAdmin):
  search_fields = ['name']

admin.site.register(Artist, ArtistAdmin)
admin.site.register(Album)
admin.site.register(Song)
admin.site.register(PlaylistEntry)
admin.site.register(UserProfile)
admin.site.register(Settings)
admin.site.register(SongDir)
admin.site.register(Emoticon)