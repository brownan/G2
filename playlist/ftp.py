# -*- coding: utf-8 -*-
import sys
import os
import threading
import time

sys.path.append('/home/jonnty/Python/pydj/pydj/playlist')
sys.path.append('/home/jonnty/Python/pydj/')
sys.path.append('/home/jonnty/')
from pyftpdlib import ftpserver
from upload import UploadedFile, UnsupportedFormatError, CorruptFileError

from pydj import settings
from django.core.management import setup_environ
setup_environ(settings)
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from pydj.playlist.models import FileTooBigError, DuplicateError


BASE_DIR = settings.FTP_BASE_DIR

class G2FTPHandler(ftpserver.FTPHandler):
  
  def __init__(self, conn, server):
    ftpserver.FTPHandler.__init__(self, conn, server)
    
  def on_file_received(self, file):
  
    def handle():
      try:
        User.objects.get(username=self.username).get_profile().uploadSong(UploadedFile(file))
      except (UnsupportedFormatError, CorruptFileError, FileTooBigError, DuplicateError):
        pass
      os.remove(file)
      self.sleeping = False
      
    self.sleeping = True
    threading.Thread(target=handle).start()

class G2Authorizer(ftpserver.DummyAuthorizer):
  def validate_authentication(self, username, password):
    try:
      self.add_user(username, 'password', BASE_DIR, perm='lwe') #list, write, CWD
    except ftpserver.AuthorizerError:
      pass #already logged in
      
    return bool(authenticate(username=username, password=password))
  
now = lambda: time.strftime("[%Y-%b-%d %H:%M:%S]")
   
def standard_logger(msg):
    f1.write("%s %s\n" %(now(), msg))
    f1.flush()
   
def line_logger(msg):
    f2.write("%s %s\n" %(now(), msg))
    f2.flush()
    
def error_logger(msg):
    f3.write("%s %s\n" %(now(), msg))
    f3.flush()
  
if __name__ == "__main__":
  try:
    f1 = open('ftpd.log', 'a')
    f2 = open('ftpd.lines.log', 'a')
    f2 = open('ftpd.error.log', 'a')
    ftpserver.log = standard_logger
    ftpserver.logline = line_logger
    ftpserver.logerror = error_logger
    authorizer = G2Authorizer()
    ftp_handler = G2FTPHandler
    ftp_handler.authorizer = authorizer
    address = ('', 2100)
    ftpd = ftpserver.FTPServer(address, ftp_handler)
    ftpd.serve_forever()
  except Exception, e:
    f2.write(e)