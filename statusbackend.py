#!/usr/bin/python
#
# This is a simple web server that runs as a backend in Varnish,
# emulating the vmod functionality we'll put into varnish in due time.
#
# Author: Lasse Karstensen <lasse.karstensen@gmail.com>

import datetime, json, os, base64, random, time, select
try:
    import json
    raise "foo"
except:
    import simplejson as json

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from pprint import pformat

NUMSAMPLES=10
pollstate = []
quickaverages = dict() # numbers from the last varnishstat run

def poll():
    global pollstate, quickaverages
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

    pollstate.insert(0, res)
    if len(pollstate) >= NUMSAMPLES:
        pollstate.pop()
    return True

def getjson():
    res = dict()
    now = datetime.datetime.now()
    res["generated_iso"] = now.isoformat()
    res["generated"] = now.strftime("%s")
    res["hostname"] = os.uname()[1]
    res["numentries"] = len(pollstate) - 1
    res["s"] = pollstate
    res["averages"] = quickaverages
    #res["responsetimes"] = resptimes() # cheat
    return json.dumps(res, indent=4)

class requesthandler(BaseHTTPRequestHandler):
    # http://docs.python.org/library/basehttpserver.html#BaseHTTPServer.BaseHTTPRequestHandler
    def do_GET(self): 
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
        elif self.path == "/json":
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

def main():
    server_address = ('0.0.0.0', 5912)
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
           poll()
       time.sleep(0.1)

if __name__ == "__main__":
    main()


