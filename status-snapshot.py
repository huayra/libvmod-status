#!/usr/bin/python

import json, random, sys, time


TODIR = "/srv/http/hyse.org/htdocs/modstatus/"
NUMSAMPLES=1000


def resptimes():
    values = []
    for i in range(NUMSAMPLES):
        values += [random.gammavariate(1,2)]
    fp = open(TODIR + "resp.json", "w+")
    json.dump(values,fp)
    fp.close()

def bucketize():
    binlevels = range(0, 1000, 50) + [100000] # millisecs
    binlevels.reverse()
    buckets = len(binlevels) * [0]
    #
    fp = open(TODIR + "hist.json", "w+")
    for i in range(NUMSAMPLES):
        value = random.gammavariate(1,2)
        value = value*1000
    #    print value
        for i in range(len(binlevels)):
            if binlevels[i] < value:
                buckets[i] = buckets[i] + 1
                break

    json.dump(buckets, fp)
    fp.close()
#    import pprint

#    for i in range(len(binlevels)):
##        # normalise
#        out = float(buckets[i]) / NUMSAMPLES
##
#        print >>fp, "%s" % (binlevels[i], out)
#pprint.pprint(binlevels)
#pprint.pprint(buckets)

if __name__ == "__main__":
    if "--repeat" in sys.argv:
        while True:
            resptimes()
            time.sleep(1)
    else:
         resptimes()
         bucketize()

