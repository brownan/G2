G2
==
Original code by Jonnty <http://gbs.fm/bugs>

G2 is a web-app to manage a playlist for a Shoutcast (or compatible) streaming
media server.

G2 acts as an internet jukebox. Listeners upload and add songs to a shared
playlist. You can also vote for and comment on the music that's playing!

If you're a Something Awful forums member, see this thread for the goon-run
gbs.fm, powered by G2:
http://forums.somethingawful.com/showthread.php?threadid=3337579

If you want to get G2 running for yourself, keep reading!

Prerequisites
=============
To install this, it probably helps to know Django well enough to configure and
deploy a project. You'll also be needing to dabble in shoutcast or icecast, so
that'll also help. Oh, and also mysql.

Requirements
============
Install these packages, for they are required for a functioning installation

* mysql-server (has some manual SQL via QuerySet.extra(), mysql is required!)
* python-mysqldb
* ices 0.4 (reads mp3 files and streams them to Shotcast). This is an old
  version, so it's easiest to build this from source. (the old version is
  necessary, the newer ices only streams ogg)
* A streaming server such as Shoutcast DNAS or Icecast.

to build icecast, you'll also need to install:
* build-essential
* python-dev
* libshout-dev
* libxml2-dev
* libmp3lame-dev

Python packages to install
--------------------------
You can pip-install these, but make sure they're installed somehow

* django
* simplejson
* mutagen
* markdown

Setting up G2
=============
The repository is a django project. It must be in a directory called "pydj",
various imports depend on it.

Mysql
-----
Create a mysql database and user, give that user full access to the database

settings.py
-----------
Create yourself a settings.py file. The easiest way is to copy the template
from::

    <django root>/conf/project_template/settings.py

Then follow these steps. They are *all* necessary, optional steps are listed
later.

* Configure your database parameters

* Add a value for SECRET_KEY. Just mash the keyboard for about 50 chars, should
  be good.

* Set ROOT_URLCONF to "pydj.urls"

* Add these items to the INSTALLED_APPS list:
  
  * django.contrib.admin
  * pydj.playlist
  * pydj.forum
  * django.contrib.markup

* Add all of the following directives and set them accordingly

  AUTH_PROFILE_MODULE
    Set this to "playlist.UserProfile"

  LOGIN_REDIRECT_URL
    set to "/playlist"
  LOGIN_URL
    set to "/login"
  TEMPLATE_CONTEXT_PROCESSORS
    Set this to::

       (
        "django.contrib.auth.context_processors.auth",
        "django.core.context_processors.debug",
        "django.core.context_processors.i18n",
        "django.core.context_processors.media",
        "django.contrib.messages.context_processors.messages",
        'playlist.context.listenersContextProcessor',
        'playlist.context.newReportsContextProcessor',
        'playlist.context.newEditsContextProcessor',
        'playlist.context.positionContextProcessor',
        'playlist.context.commentProcessor',
        'playlist.context.nowPlayingContextProcessor',
        'playlist.context.SQLLogContextProcessor',
        'playlist.context.siteContext',
        ) 
    
  IMAGES_DIR
    G2 is configured to serve static content itself out of this directory. Set
    this setting to the absolute path on the filesystem to the images
    directory, which is in the playlist directory.

  LOGIC_DIR
    Set this to the absolute path to the logic directory within the playlist
    directory. This is the ices working directory, and G2 looks in here for the
    ices.cue file

  SHOW_QUERIES
    Set this to False. You don't want this on.

  ICES_CONF
    Set this to the absolute path to your ices.conf file, which is usually in
    the logic directory. This settings is passed into "ices -c ICES_CONF", and
    just used to start ices from the admin panel

  STREAMINFO_URL
    Set this to the url of the shoutcast server. This url is queried and
    scraped for the listener count. Currently, this only works with icecast
    servers.

  NEXT_PASSWORD
    Set this to something random and secret. It's used for the ices streaming
    source to query G2 for the next song to play.

  MAX_UPLOAD_SIZE
    Set this to the maximum allowed upload size, in bytes.

  MAX_SONG_LENGTH
    Set this to the maximum allowed song length, in seconds. Longer songs may
    still be uploaded, but will be auto-banned.

  PLAYLIST_MAX
    Set this to the maximum number of songs each user can have in playlist at a time

  PLAYLIST_SOFT_TIME_LIMIT
    Set this to the maximum number of minutes a user can occupy on the
    playlist. This is a soft limit, they can add a song that exceeds this
    limit, but cannot add more songs after that. In other words, if their time
    on the playlist exceeds this value, they cannot add more songs.

  REPLAY_INTERVAL
    Set this to the time until a song can be added again, in hours

  IS_LIVE
    Doesn't do anything at the moment, but you still need to define it. Set to
    false, I guess.

  FILE_UPLOAD_MAX_MEMORY_SIZE
    Set this to 0

  SITE_TITLE
    Set to the site's title, which will be displayed in the page title on every
    page

  LISTEN_URL
    Set this to the URL that the Listen link should point to.

Other directives, not documented yet
------------------------------------
They're not strictly necessary for a working install, but may do something
interesting. I haven't gotten around to documenting this yet

*  ROOT_PATH
*  LOG_LEVEL
*  LOG_FILENAME
*  FORUM_MAIL_PREFIX
*  FORUM_MAIL_FROM
*  DEFAULT_FROM_EMAIL
*  FTP_BASE_DIR

Post Config
-----------
Now that your settings.py is nice and configured, run

::
    
    python manage.py syncdb

to populate the database. Create yourself an admin user when propmpted.

Now deploy the site with apache+mod_wsgi, or lighttpd, or the django built in
server, or whatever. This is left as an excercise to the reader.

A wsgi file is provided under the ``apache`` directory.

Note: you may need to add some creative path additions to the top of some
files. If you have custom paths to add, do so to these files:

* apache/django.wsgi
* manage.py
* playlist/ftp.py
* playlist/logic/ices.py

Database setup
--------------
Before you can use the site, a couple things need to be added to the database.
Head to the admin site at ``/admin``

* Go to the ``Settingss`` model and add a new ``settings`` with key
  ``welcome_message`` and whatever value.

* Go to the ``Song dirs`` model and add at least one usable song dir so G2 has
  somewhere to save the songs. The path should be an absolute path on the local
  filesystem to a *writable* directory to the web server.

  ``Hash letters`` is a number. If greater than 0, songs are put into sub
  directories named after this many hash letters from the song's hash. If you
  don't expect many songs, 0 is fine. Otherwise, 1 or 2 is a good choice. More
  just seems unnecessary to me, but be your own judge on that.

* Go to the Groups model and add a group for your listeners. At a minimum, this
  group should contain these permissions so listeners can view a functioning
  site:

  * Can view artist pages
  * Can add song to the playlist
  * Can view the playlist
  * Can upload songs
  * Can view user pages
  * Can view song pages

Adding Users
------------
Currently, adding users is a manual process. I stripped out the original
Something Awful integrated login used at gbs.fm, but haven't added anything in
its place.

To add a user, head to the admin page and follow these steps:

* Add a user to the Users model

  * Once added, go back to edit them into the Listeners group.

* Go to the ``User profiles`` model and add a new profile for that user.

Shoutcast/Icecast Setup
=======================
Set up a shotcast or icecast server. On ubuntu, these steps suffice:

* Install the package ``icecast2``
* Edit ``/etc/icecast2/icecast.xml`` and change the passwords.
* Edit ``/etc/default/icecast2`` to enable the service
* Start the service with ``sudo service icecast2 start``

Icecast is now running on port 8000. Remember that, and the password you used
for the next step.

ICES Setup
==========
The web app is all set up, but you still need to get ices set up

* Download, compile, and install ices 0.4 (requires libshout-dev, libxml2-dev, libmp3lame-dev)
* Put the provided sample ices.conf and ices.py in the logic dir.
* Edit ices.py for the correct paths to the django project and the correct NEXT_URL
* Edit ices.conf

  * Set BaseDirectory to your logic directory
  * Make sure <Type> is ``python`` and <Module> is ``ices``
  * Set the <Server> section appropriately for your shoutcast/icecast server.
    Make sure Protocol is set right, see the comments in the sample conf.
  * Set the <Name>, <Genre>, <Description>, and <URL> to whatever you want.
  * Make sure <Background> is ``1``

* Go to the g2admin page on the site, and press the start_stream link. This
  will launch ices.
  
If all works, things are now streaming! Otherwise, check the ices logs in the
logic directory and the shoutcast/icecast logs for clues.

FTP Setup
=========
* ftp.py is the ftp server
* Requires pyftpdlib to run (pip install)
* Edit paths as appropriate at the top. Needs to have pydj and playlist and playlist contents in path
* Edit FTP_BASE_DIR in settings.py to a writable directory for temporary storage of uploaded files
* Now run ftp.py. Try running in the background with nohup

