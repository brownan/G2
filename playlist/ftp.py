# -*- coding: utf-8 -*-
import sys
import os
import threading

sys.path.append('/home/jonnty/Python/pydj/pydj/playlist')
sys.path.append('/home/jonnty/Python/pydj/')
from pyftpdlib import ftpserver
from upload import UploadedFile

from pydj import settings
from django.core.management import setup_environ
setup_environ(settings)
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


BASE_DIR = settings.FTP_BASE_DIR

class G2FTPHandler(ftpserver.FTPHandler):
  
  def __init__(self, conn, server):
    ftpserver.FTPHandler.__init__(self, conn, server)
    
  def on_file_received(self, file):
  
    def handle():
      User.objects.get(username=self.username).get_profile().uploadSong(UploadedFile(file))
      os.remove(file)
      self.sleeping = False
      
    self.sleeping = True
    threading.Thread(target=handle).start()

class G2Authorizer(ftpserver.DummyAuthorizer):
  def validate_authentication(self, username, password):
    try:
      self.add_user(username, 'password', BASE_DIR, perm='lw')
    except ftpserver.AuthorizerError:
      pass #already logged in
      
    return bool(authenticate(username=username, password=password))
  
if __name__ == "__main__":
    authorizer = G2Authorizer()
    ftp_handler = G2FTPHandler
    ftp_handler.authorizer = authorizer
    address = ('', 2100)
    ftpd = ftpserver.FTPServer(address, ftp_handler)
    ftpd.serve_forever()