#!/usr/bin/python
#
# This is a simple web server that runs as a backend in Varnish,
# emulating the vmod functionality we'll put into varnish in due time.
#
# Author: Lasse Karstensen <lasse.karstensen@gmail.com>

# A list of IP addresses which is allowed to access this webserver.
# Please note that they are string matched against the client ip, so no CIDR for you.
IP_WHITELIST=["127.0.0.1", "::1",
    "194.31.39.", "2a02:c0:1013:", # varnish software
    ]

import datetime, os, base64, random, time, select, popen2, socket
# attempt at supporting Python 2.5.
try:
    import json
except ImportError:
    import simplejson as json

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from pprint import pformat


NUMSAMPLES=10
pollstate = []
quickaverages = dict() # numbers from the last varnishstat run
stored_varnish_version = None

def run_varnishstat():
    res = dict()
    # dont assume varnishstat with json support
    lines = os.popen("varnishstat -1").readlines()
    for line in lines:
        l = line.split()
        # very nasty
        res[l[0]] = l[1]
        if l[2] != ".":
            quickaverages[l[0]] = l[2]
    now = datetime.datetime.now()
    res["generated_iso"] = now.isoformat()
    res["generated"] = now.strftime("%s")
    return res

def poll_varnishstat():
    global pollstate, quickaverages
    res = run_varnishstat()
    pollstate.insert(0, res)
    if len(pollstate) >= NUMSAMPLES:
        pollstate.pop()
    return True

def varnish_version():
    # avoid fork on every page lookup.
    global stored_varnish_version
    if stored_varnish_version:
        return stored_varnish_version

    # will probably not work if you are rolling your own varnishd.
    (_out, _in, localstderr) = popen2.popen3("/usr/sbin/varnishd -V")
    versionstring = localstderr.readline()
    _x, majorversion, _x, gitid = versionstring.split()
    stored_varnish_version = dict()
    stored_varnish_version["varnishd"] = majorversion[1:] # remove (
    stored_varnish_version["commit"] = gitid[:-1] # remove )
    return stored_varnish_version


def parse_backends(inputdict):
    """
        Read varnistat output and pull out a list of backends. Should be done in JS, but python
	is so much easier.
    """
    res = dict()
    for key in inputdict.keys():
        if not key.startswith("VBE"):
	    continue
	name, infostring = key[4:].split("(", 1)
	v4,v6,port = infostring.split(",", 2)
	port = port.split(")", 1)[0]
	if len(v6) == 0: v6 = None
	if len(v4) == 0: v4 = None
	res[name] = {'name': name,
		'keyname': ",".join(key.split(".")[:-1]),
		'IPv4': v4,
		'IPv6': v6,
		'port': port}
    return res
  
def prepare_backendstring(backends):
    "should be put into js real soon now."
    if len(backends) == 0: 
        return "<p>No backends seen in varnishstat</p>"
    r = ["<ul>"]
    for key, backend in backends.items():
        s = "<li>%s (%s:%s)" % (backend["name"], backend["IPv4"], backend["port"])
        r.append(s)
    r.append("</ul>")
    return "".join(r)


def getjson():
    res = dict()
    now = datetime.datetime.now()
    res["generated_iso"] = now.isoformat()
    res["generated"] = now.strftime("%s")
    res["hostname"] = os.uname()[1]
    res["numentries"] = len(pollstate) - 1
    res["version"] = varnish_version()
    res["backends"] = parse_backends(pollstate[0])
    # VERY QUICK WIN. NASTY
    res["backends_text"] = prepare_backendstring(res["backends"])
    res["s"] = pollstate
    res["averages"] = quickaverages
    #res["responsetimes"] = resptimes() # cheat
    return json.dumps(res, indent=4)

class requesthandler(BaseHTTPRequestHandler):
    # http://docs.python.org/library/basehttpserver.html#BaseHTTPServer.BaseHTTPRequestHandler
    def do_GET(self): 
        # simple authentication
	allowed = False
	clientip = self.client_address[0]
	# Filter off any IPv4-mapped info in the beginning of the string.
	clientip = clientip.replace("::ffff:", "")

	for allowedip in IP_WHITELIST:
	    if clientip.startswith(allowedip):
	        allowed = True
		break
        if not allowed:
            self.send_response(403, "Forbidden")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
	    self.wfile.write("%s is not allowed. See the IP_WHITELIST entry\n" % clientip)
	    return

        # eat GET-args
#        if "?" in self.path:
#            self.path = self.path[0:self.path.index("?")]


        if self.path == "/":
            self.path = "index.html"
        if self.path == "/favicon.ico":
            self.send_response(200, "OK")
            self.send_header("Content-Type", "image/x-icon")
            self.end_headers()
            self.wfile.write(favicon())
	# either this, or pull from the dict in /fullstatus
        elif self.path == "/version":
            self.send_response(200, "OK")
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "maxage=3600")
            self.end_headers()
            self.wfile.write(json.dumps(varnish_version()))
        elif self.path == "/varnishstat_realtime":
            self.send_response(200, "OK")
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "max-age=10")
            self.end_headers()
            self.wfile.write(json.dumps(run_varnishstat()))
        elif self.path == "/fullstatus":
            self.send_response(200, "OK")
            self.send_header("Content-Type", "application/json")
            self.send_header("Expires", "Fri, 30 Oct 1998 14:19:41 GMT")
            self.end_headers()
            self.wfile.write(getjson())
        else:
            possible_source = "web/%s" % self.path
            if not os.path.exists(possible_source):
                self.send_error(404, "Not found")
                self.end_headers()
                return
            self.send_response(200, "OK")
            self.send_header("Expires", "Fri, 30 Oct 1998 14:19:41 GMT")

            # made by the dirty hacks department.
            content_type = "text/html"
            if possible_source.endswith(".css"): content_type = "text/css"
            elif possible_source.endswith(".js"): content_type = "application/javascript"
            elif possible_source.endswith(".png"): content_type = "image/png"

            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(open(possible_source, "r").read())

def favicon():
    """http://www.favicon.cc/ is the man!"""
    s = """AAABAAEAEBAAAAAAAABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwUDP8cFAz/HBQM/xwUDP8cFAz/HBQM/xwUDP8cFAz/HBQM/xwUDP8cFAz/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHBQM/xwUDP8cFAz/HBQM/xwUDP8cFAz/HBQM/xwUDP8cFAz/HBQM/xwUDP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcFAy0HBQMtBwUDLQcFAy0HBQMtBwUDLQcFAy0HBQMtBwUDLQcFAy0HBQMtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/hAD//4QA//+EAP//hAD//4QA//+EAP//hAD//4QA/wAAAAAAAAAAAAAAAAAAAAB1SRm0dUkZtAAAAAAAAAAA/4QA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP+EAP//hAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP+EAP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdUkZtP+EAP8AAAAAAAAAAHVJGbR1SRm0AAAAAAAAAAD/hAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/hAD/AAAAAAAAAAB1SRm0dUkZtAAAAAAAAAAA/4QA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/4QA/wAAAAAAAAAAdUkZtHVJGbQAAAAAAAAAAP+EAP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP+EAP8AAAAAAAAAAHVJGbR1SRm0AAAAAAAAAAD/hAD//4QA//+EAP//hAD//4QA//+EAP//hAD//4QA//+EAP//hAD/AAAAAAAAAAB1SRm0dUkZtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAPABAAD//wAA8AEAAP//AADwAQAA//8AAP//AACAeQAAvz8AAL+ZAAC/2QAAv9kAAL/ZAACAGQAA//8AAA=="""
    return base64.b64decode(s)

def resptimes():
    return [ random.gammavariate(1,2) for i in range(100)]

def hist():
    binlevels = range(0, 1000, 50) + [100000] # millisecs
    binlevels.reverse()
    buckets = len(binlevels) * [0]
    fp = open(TODIR + "hist.json", "w+")
    for i in range(NUMSAMPLES):
        value = random.gammavariate(1,2)
        value = value*1000
    #    print value
        for i in range(len(binlevels)):
            if binlevels[i] < value:
                buckets[i] = buckets[i] + 1
                break

class IPv6AlsoHTTPServer(HTTPServer):
    def server_bind(self):
        print dir(HTTPServer)
	print HTTPServer.address_family
	import socket
	HTTPServer.socket_type = socket.AF_INET6
        HTTPServer.server_bind(self)

def main():
    # This is needed to make the TCPServer listen do AF_INET6 with mapped IPv4.
    HTTPServer.address_family = socket.AF_INET6

    server_address = ('', 5912)
    httpd = HTTPServer(server_address, requesthandler)

    pollobj = select.poll()
    pollobj.register(httpd.fileno())

    # yes yes, it will not answer http requests when polling. sufficient for our use.
    lastpoll = 0.0
    while True:
       pollres = pollobj.poll(0)
       if len(pollres) > 0:
           httpd.handle_request()

       now = time.time()
       if now > (lastpoll + 2):
           lastpoll = now
           poll_varnishstat()
       time.sleep(0.1)

if __name__ == "__main__":
    main()


