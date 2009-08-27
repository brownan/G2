# -*- coding: utf-8 -*-
from pydj.playlist.models import *
from django.contrib import admin

admin.site.register(Artist)
admin.site.register(Album)
admin.site.register(Song)
admin.site.register(PlaylistEntry)
admin.site.register(UserProfile)
admin.site.register(Settings)