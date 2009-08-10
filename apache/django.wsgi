import os
import sys
sys.path.extend(['/home/jonnty/', '/home/jonnty/pydj/dbsettings'])

os.environ['DJANGO_SETTINGS_MODULE'] = 'pydj.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()