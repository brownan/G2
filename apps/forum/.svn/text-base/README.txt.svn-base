============
Django Forum
============

This is a very basic forum application that can plug into any
existing Django installation and use it's existing templates,
users, and admin interface. 

It's perfect for adding forum functionality to an existing website.

Development was done on Django SVN rev. 5007. YMMV on other revisions.

Please send comments/suggestions to me directly, ross at rossp dot org.

Google Code Page / SVN: http://code.google.com/p/django-forum/
My Home Page: http://www.rossp.org

Current Status
--------------

 * It's very basic in terms of features, but it works and is usable.
 * Uses Django Admin for maintenance / moderation - no in-line admin.
 * Uses existing django Auth and assumes you already have that up and
   running. I use and recommend django-registration [1]
 * Roll your own site with little work: Install Django, install
   django-registration, flatpages, django-forum, setup your templates
   and you have an instant website :)
 * Requires a very recent Django SVN checkout, at least 7971 (1.0 alpha is OK)
 * Requires python-markdown, and 'django.contrib.markup' in INSTALLED_APPS.

[1] http://code.google.com/p/django-registration/

Getting Started
---------------

   1. Checkout code via SVN into your python path.
       svn co http://django-forum.googlecode.com/svn/trunk/ forum
   3. Add 'forum' to your INSTALLED_APPS in settings.py. Also add 
       'django.contrib.markup' if you haven't already got it there.
   4. ./manage.py syncdb
   5. Update urls.py: (r'^forum/', include('forum.urls')),
   6. Go to your site admin, add a forum
   7. Browse to yoursite.com/forum/
   8. Enjoy :)

Note: The forum software can be at any URI you like, just change the relevant
urls.py entry. EG replace 'forum/' with '/' to have your forum at the root 
URI, or 'mysite/community/forum/' - whatever you need.

Note: You can include the forum sitemaps in your main sitemap index.
Example:

    from forum.urls import sitemap_dict as forum_sitemap

    yoursitemap_dict.update(forum_sitemap)

    urlpatterns = patterns('',
        (r'^sitemap.xml$', 'django.contrib.sitemaps.views.index', {'sitemaps': yoursitemap_dict}),
        (r'^sitemap-(?P<section>.+)\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': yoursitemap_dict}),
    )

Thanks
------

The following people have contributed code or ideas to this project. Thank 
you for all of your efforts:

* mandric
* Eric Moritz
* A. Alibrahim
* marinho
* canburak
* Erik Wickstrom
* Aron Jones
* Sir Steve H
* xphuture
