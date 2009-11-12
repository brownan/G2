import re
from urllib2 import urlopen, URLError
import urllib2
import cookielib
from urllib import quote, urlencode

from django.conf import settings

login_addr = "http://forums.somethingawful.com/account.php"
profile_addr = "http://forums.somethingawful.com/member.php?action=getinfo&username="

username = settings.SA_USERNAME
password = settings.SA_PASSWORD

userid = re.compile(r'<input type="hidden" name="userid" value="(\d+)">')


randcode = lambda: md5(str(getrandbits(64))).hexdigest()



class SAProfile:
  
  def __init__(self, username):
    """Login and load the profile page. Error handling left to caller."""
    cj = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)
    args = urlencode([("username", username), ("password", password), ("action", "login")])
    opener.open(login_addr, args) #login
    self.page = opener.open(profile_addr + quote(username)).read()
    
  def get_id(self):
    return int(userid.search(self.page).group(1))
  
  def has_authcode(self, code):
    return code in self.page

if __name__ == "__main__":
  p = SAProfile("Jonnty")
  print p.get_id()
  print p.has_authcode("31bd8012609e680010f1792454dd751")
    
    