# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
import pydj.playlist.views


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
(r'^playlist', 'pydj.playlist.views.playlist'),
(r'^$', 'pydj.playlist.views.playlist'),
(r'^images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/jadh/Python/pydj/pydj/playlist/images'}),
(r'^upload/?$', 'pydj.playlist.views.upload'),
(r'^search/?$', 'pydj.playlist.views.search'),
(r'^comment/(\d+)$', 'pydj.playlist.views.comment'),
(r'^artist/(?P<artistid>\d+)$', 'pydj.playlist.views.artist'),
(r'^user/(?P<userid>\d+)$', 'pydj.playlist.views.user'),
(r'^.*/images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/jadh/Python/pydj/pydj/playlist/images'}),
(r'^login/?$', 'django.contrib.auth.views.login', {'template_name': 'playlist/login.html'}),
(r'^logout/?$', 'django.contrib.auth.views.logout'),
(r'^add/(?P<songid>\d+)$', 'pydj.playlist.views.add'), 
(r'^next/(?P<authid>.+)$', 'pydj.playlist.views.next'), 
(r'^register/?$', 'pydj.playlist.views.register'), 
(r'^song/(\d+)(/edit)?$', 'pydj.playlist.views.song', {}, "song"),
(r'^song/(\d+)/rate/(\d)$', 'pydj.playlist.views.rate'),
(r'^song/(\d+)/ban$', 'pydj.playlist.views.bansong'),
(r'^song/(\d+)/unban/?(\d+)$', 'pydj.playlist.views.unbansong'),

#(r'', 'django.contrib.auth.views.redirect_to_login', {'next': 'playlist'}),




)
