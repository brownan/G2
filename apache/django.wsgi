import os
import sys
sys.path.append('/home/jadh/')

os.environ['DJANGO_SETTINGS_MODULE'] = 'pydj.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

