__version__ = "0.3"
__date__ = "2008-05-09"
__author__ = "Denis Laprise - denis@poly9.com"
__url__ = "http://code.google.com/p/pyetrade/"

import urllib2, urllib, re


class CookieJar:

    def __init__(self):
        self._cookies = {}

    def extractCookies(self, response, nameFilter = None):
        for cookie in response.headers.getheaders('Set-Cookie'):
            name, value = (cookie.split("=", 1) + [""])[:2]
            if not nameFilter or name in nameFilter:
                self._cookies[name] = value.split(";")[0]


    def addCookie(self, name, value):
        self._cookies[name] = value

    def hasCookie(self, name):
        return self._cookies.has_key(name)

    def setCookies(self, request):
        request.add_header('Cookie',
                           "; ".join(["%s=%s" % (k,v)
                                     for k,v in self._cookies.items()]))

class GHTTPCookieProcessor(urllib2.BaseHandler):
    def __init__(self, cookieJar):
        self.cookies = cookieJar
        
    def https_response(self, request, response):
        self.cookies.extractCookies(response)
        return response

    def https_request(self, request):
        self.cookies.setCookies(request)
        return request

GHTTPCookieProcessor.http_request = GHTTPCookieProcessor.https_request
GHTTPCookieProcessor.http_response = GHTTPCookieProcessor.https_response

class LoginFailure(Exception):
 pass

class Session:
    """
        An abstract class to represent an E*Trade session. Handle login and subsequent cookie dance.
    """
    def __init__(self, username, password):
        self._cookies = CookieJar()
	self._username = username
	self._password = password
        
    def doLogin(self):
        """
        A login method which can be used to log to E*Trade
        """
	raise NotImplementedError
        
    def getPage(self, url, post_data=None):
        """
        Gets the url URL with cookies enabled. Posts post_data.
        """
        req = urllib2.build_opener(GHTTPCookieProcessor(self._cookies))
        f = req.open(self._encode(url), data=urllib.urlencode(post_data))
        if f.headers.dict.has_key('set-cookie'):
            self._cookies.extractCookies(f)
        return f

    def _encode(self, value): # This method is copyright (C) 2004, Adrian Holovaty
        """
        Helper method. Google uses UTF-8, so convert to it, in order to allow
        non-ASCII characters.
        """
        if isinstance(value, unicode):
            value = value.encode("utf-8")
        return value

class CanadaSession(Session):
	def __init__(self, username, password):
		Session.__init__(self, username, password)

	def doLogin(self):
		url = "https://swww.canada.etrade.com/login.fcc"	
		params = {'TARGET' : "/cgi-bin/cwRedirection.cgi", 'USER' : self._username, 'PASSWORD' : self._password}
		p = self.getPage(url, params)
		if not self._cookies.hasCookie('SMSESSION'):
			raise LoginFailure
		return self

