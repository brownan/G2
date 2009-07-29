# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
import pydj.playlist.views
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^pydj/', include('pydj.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
url(r'^admin/(.*)', admin.site.root, {}, "admin_site"),
(r'^$', 'pydj.playlist.views.playlist', {}, "playlist"),
(r'^playlist(/?|(?P<js>/js))$', 'pydj.playlist.views.playlist'),
(r'^images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.IMAGES_DIR}),
(r'^upload/?$', 'pydj.playlist.views.upload'),
(r'^search/?$', 'pydj.playlist.views.search'),
(r'^comment/(\d+)$', 'pydj.playlist.views.comment'),
(r'^artist/(?P<artistid>\d+)$', 'pydj.playlist.views.artist', {}, "artist"),
(r'^user/(?P<userid>\d+)$', 'pydj.playlist.views.user'),
(r'^.*/images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.IMAGES_DIR}),
(r'^login/?$', 'django.contrib.auth.views.login', {'template_name': 'playlist/login.html'}),
(r'^logout/?$', 'django.contrib.auth.views.logout'),
(r'^add/(?P<songid>\d+)$', 'pydj.playlist.views.add'), 
(r'^next/(?P<authid>.+)$', 'pydj.playlist.views.next'), 
(r'^register/?$', 'pydj.playlist.views.register'), 
(r'^song/(\d+)(/edit)?$', 'pydj.playlist.views.song', {}, "song"),
(r'^song/(\d+)/rate/(\d)$', 'pydj.playlist.views.rate'),
(r'^song/(\d+)/ban$', 'pydj.playlist.views.bansong'),
(r'^song/(\d+)/delete$', 'pydj.playlist.views.deletesong'),
(r'^song/(\d+)/unban/?(\d+)$', 'pydj.playlist.views.unbansong'),
(r'^playlist/remove/(\d+)$', 'pydj.playlist.views.removeentry'), 
(r'^skip$', 'pydj.playlist.views.skip'), 
(r'^artists/(\d*)$', 'pydj.playlist.views.listartists'), 
(r'^ajax/(?P<resource>.+)$', 'pydj.playlist.views.ajax'), 
(r'^g2admin$', 'pydj.playlist.views.g2admin', {}, 'g2admin'), 
(r'^stop_stream$', 'pydj.playlist.views.stop_stream', {}, 'stop_stream'), 
(r'^start_stream$', 'pydj.playlist.views.start_stream', {}, 'start_stream'), 

#javascript stuff
(r'^artist/$', 'pydj.playlist.views.artist', {}, "artist_js"),
(r'^song/$', 'pydj.playlist.views.song', {}, "song_js"),
(r'^user/$', 'pydj.playlist.views.user', {}, "user_js"),
(r'^playlist/remove/$', 'pydj.playlist.views.removeentry', {}, "removeentry_js"), 

#(r'', 'django.contrib.auth.views.redirect_to_login', {'next': 'playlist'}),




)
