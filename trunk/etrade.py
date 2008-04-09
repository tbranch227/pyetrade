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

class InvalidMarketError(Exception):
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
	req.addheaders = [('User-agent', "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)")]
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

    def _getOptionUrl(self):
	raise NotImplementedError

    def _validateMarket(self, market):
	raise NotImplementedError

    def fetchOption(self, symbol, market):
	mv = self._validateMarket(market)
	url = self._getOptionUrl()
	params = {'__T_1_1__2FAnalysisRequest_2Foscar_2FSYM' : symbol, '__T_2_1__2FAnalysisRequest_2Foscar_2FXXREG' : mv, '__T_4_1__2FAnalysisRequest_2Foscar_2FXXIOA' : 'A', '__T_3_1__2FAnalysisRequest_2Foscar_2FXXCPB' : 'B'}
	p = self.getPage(url, params).read()
	result = []
	re_opt = re.compile('<td align="left" colspan="20"><b>Options Expiration: </b>([^<]+)</td>(.*?)(<tr bgcolor="#ffffff">|</tbody>)', re.M | re.S)	
	opts = re_opt.findall(p)
	re_tr = re.compile('<td class="[^"]+">([^<]+)</td><td class="[^"]+">([^<]+)</td><td class="[^"]+">([^<]+)</td><td class="[^"]+"><span style="[^"]+">([^<]+)</span></td><td class="[^"]+">([^<]+)</td><td class="[^"]+">([^<]+)</td><td class="[^"]+">([^<]+)</td><td bgcolor="[^"]+"><font color="[^"]+">([^<]+)</font></td>')
	for expiration, data, n in opts:
		o = re_tr.findall(data)
		for i in range(0, len(o)-1, 2):
			result.append(o[i] + ('call', ))
			result.append(o[i+1] + ('put', ))
	return result


class CanadaSession(Session):
	def __init__(self, username, password):
		Session.__init__(self, username, password)
		self._markets = {'U.S.' : 'A', 'CDN' : 'C'}

	def doLogin(self):
		url = "https://swww.canada.etrade.com/login.fcc"	
		params = {'TARGET' : "/cgi-bin/cwRedirection.cgi", 'USER' : self._username, 'PASSWORD' : self._password}
		p = self.getPage(url, params)
		if not self._cookies.hasCookie('SMSESSION'):
			raise LoginFailure
		return self

	def _getOptionUrl(self):
		return "https://canada.etrade.ultraoptions.com/analysis.jsp"

	def _validateMarket(self, market):
		if not market in ['U.S.', 'CDN']:
			raise InvalidMarketError
		return self._markets[market]

