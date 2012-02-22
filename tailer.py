#!/usr/bin/python

import subprocess, os, sys


def main():
    sessions = dict()
    print "foo"
    while True:
        line = sys.stdin.readline().strip()
        l = line.split()
        #print "l is: ", l
        if l[1] == "ReqEnd":
            #print "time-to-first-byte er: %s" % l[6]
            print l[6]
#            print "time-to-first-byte er: %s" % l[6]
            #print "transfer-time er: %s" % l[7]


if __name__ == "__main__":
    main()
