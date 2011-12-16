#!/usr/bin/python

import os
import sys
import optparse
from ConfigParser import ConfigParser

from cluster import Cluster

defaults = {
        'hosts'     : 'localhost',
        'uri'       : 'qemu+ssh://%s/system',
        'headers'   : 'false',
        'selector'  : 'mem',
        }

def parse_args():
    p = optparse.OptionParser()
    p.allow_interspersed_args = False
    p.add_option('-f', '--config', default='/etc/libvirt/cluster.conf')
    p.add_option('-H', '--headers', action='store_true')
    return p.parse_args()

def main():
    opts, args = parse_args()

    if opts.headers:
        defaults['headers'] = 'true'

    config = ConfigParser(defaults)
    config.read(opts.config)

    if not config.has_section('cluster'):
        config.add_section('cluster')

    cluster = Cluster(config)

    if not args:
        args = [ 'list' ]

    cmd = args.pop(0)
    cluster.dispatch(cmd, args)

if __name__ == '__main__':
    main()

