# -*- coding: utf-8 -*-
"""
URLConf for Django-Forum.

django-forum assumes that the forum application is living under
/forum/.

Usage in your base urls.py:
    (r'^forum/', include('forum.urls')),

"""

from django.conf.urls.defaults import *
from forum.models import Forum
from forum.feeds import RssForumFeed, AtomForumFeed
from forum.sitemap import ForumSitemap, ThreadSitemap, PostSitemap

feed_dict = {
    'rss' : RssForumFeed,
    'atom': AtomForumFeed
}

sitemap_dict = {
    'forums': ForumSitemap,
    'threads': ThreadSitemap,
    'posts': PostSitemap,
}

urlpatterns = patterns('',
    url(r'^$', 'forum.views.forums_list', name='forum_index'),
    
    url(r'^(?P<url>(rss|atom).*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict}),

    url(r'edit/(?P<postid>[0-9]+)/$', 'forum.views.edit_post', name='post_edit'),

    url(r'^thread/(?P<thread>[0-9]+)/(?P<lastread>lastread)?$', 'forum.views.thread', name='forum_view_thread'),
    url(r'^thread/(?P<thread>[0-9]+)/editing/(?P<editid>[0-9]+)$', 'forum.views.thread', name='thread_post_edit'),
    url(r'^thread/(?P<thread>[0-9]+)/reply/$', 'forum.views.reply', name='forum_reply_thread'),
    url(r'^thread/(?P<threadid>[0-9]+)/action/(?P<action>[a-z]+)$', 'forum.views.mod_action', name='mod_action'),
    
    url(r'^subscriptions/$', 'forum.views.updatesubs', name='forum_subscriptions'),

    url(r'^(?P<slug>[-\w]+)/$', 'forum.views.forum', name='forum_thread_list'),
    url(r'^(?P<forum>[-\w]+)/new/$', 'forum.views.newthread', name='forum_new_thread'),

    url(r'^([-\w/]+/)(?P<forum>[-\w]+)/new/$', 'forum.views.newthread'),
    url(r'^([-\w/]+/)(?P<slug>[-\w]+)/$', 'forum.views.forum', name='forum_subforum_thread_list'),

    (r'^sitemap.xml$', 'django.contrib.sitemaps.views.index', {'sitemaps': sitemap_dict}),
    (r'^sitemap-(?P<section>.+)\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemap_dict}),
)
