# -*- coding: utf-8 -*-
from django.core.management import setup_environ
import sys
import os
sys.path.append('/home/jonnty/Python/pydj/pydj/playlist')
from pydj import settings
import threading
#from pydj.playlist.upload import UploadedFile
from pyftpdlib import ftpserver

BASE_DIR = settings.FTP_BASE_DIR

setup_environ(settings)

#from django.contrib.auth.models import User,  UserManager, Group, Permission
from django.contrib.auth import authenticate


class G2FTPHandler(ftpserver.FTPHandler):
  
  def __init__(self, conn, server):
    ftpserver.FTPHandler.__init__(self, conn, server)
    
  def on_file_received(self, file):
  
    def handle():
      #u = UploadedFile(file)
      #u.process()
      os.rename(file, file+'aaa')
      self.sleeping = False
      
    self.sleeping = True
    threading.Thread(target=handle).start()

class G2Authorizer(ftpserver.DummyAuthorizer):
  def validate_authentication(self, username, password):
    self.add_user(username, 'password', BASE_DIR, perm='lw')
    return bool(authenticate(username=username, password=password))
    
  #def get_msg_login(self, user):
    #return "Hello. Insert dongs here."
  
  #def get_home_dir(self, user):
    #return BASE_DIR
  
  #def get_perms(self, user):
    #return 'lw'
    
  #def has_perm(self, user, perm, path=None):
    #if path is None:
      #return perm in 'lw'
    #else:
      #return perm in 'lw' and (path == BASE_DIR)
  
if __name__ == "__main__":
    authorizer = G2Authorizer()
    ftp_handler = G2FTPHandler
    ftp_handler.authorizer = authorizer
    #ftp_handler.abstracted_fs.root = BASE_DIR
    address = ('', 2100)
    ftpd = ftpserver.FTPServer(address, ftp_handler)
    ftpd.serve_forever()