Status page for Varnish
=======================


The idea is to provide a quick summary of the current status of your Varnish
cache on a HTML page, much like Other Caches[tm], webservers (mod_status) and
load balancers have.

Planned implementation includes:

* a backend that exports n samples of the varnishstat counter set via JSON. Map it into your URL-space in VCL. 
* the backend provide you with some HTML that polls the JSON and show this to the user.

Anyone wishing to roll their own metrics can just poll the JSON for themselves.

Ideas:

* use socket.io for polling.
* use highcharts (or flot) to do some simple graphs.

