Status page for Varnish
=======================


The idea is to provide a quick summary of the current status of your Varnish
cache on a HTML page, much like Other Caches[tm], webservers (mod_status) and
load balancers have.

Overall plans:
* we'll do a sample-and-hold vmod that stores counters every n seconds and keeps m samples of it. This is done inside varnish.
* (for now this is just a python daemon, to keep going forward)
* the vmod/daemon makes this visible in a sub-URL of your site that you define in VCL.
* the sub-URL provides you with: 1) JSON representation of the stored samples, 2) HTML+Javascript to render it.

Anyone wishing to roll their own metrics can just poll the JSON for themselves.

What we have:
* statusbackend.py runs a HTTPd on port 5912 and serves files in web/. /json is hardcoded in the server and outputs json.
* web/index.html needs some love.

Maybees:
* use socket.io for polling.
* use highcharts (or flot) to do some simple graphs.

