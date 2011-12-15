#!/usr/bin/python

import os
import sys
import optparse

from ConfigParser import ConfigParser
import libvirt

defaults = {
        'hosts'     : 'localhost',
        'uri'       : 'qemu+ssh://%s/system',
        'headers'   : 'false',
        }

class Cluster (object):

    def __init__ (self, config):
        self.config = config
        self.hosts = config.get('cluster', 'hosts').split()
        libvirt.registerErrorHandler(self.errorHandler, None)

    def errorHandler(self, ctx, error):
        pass

    def lookupByName(self, name):
        for conn in self.connections():
            try:
                dom = conn.lookupByName(name)
                return (conn.getURI(), dom)
            except libvirt.libvirtError, detail:
                if detail.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                    continue
                else:
                    raise

    def listAllDomains(self):
        for conn in self.connections():
            for domid in conn.listDomainsID():
                dom = conn.lookupByID(domid)
                yield(conn.getURI(), dom.name(), dom)

    def uris(self):
        uritemplate = self.config.get('cluster', 'uri')
        for host in self.hosts:
            yield uritemplate % host

    def connections(self):
        for uri in self.uris():
            try:
                yield libvirt.openReadOnly(uri)
            except libvirt.libvirtError, detail:
                print >>sys.stderr, 'ERROR: %s: %s' % (
                        uri, detail.get_error_message())
                continue

    def dispatch(self, cmd, args):
        if hasattr(self, 'cmd_%s' % cmd):
            getattr(self, 'cmd_%s' % cmd)(args)
        else:
            raise NotImplementedError(cmd)

    def cmd_list(self, args):
        '''List all domains running on the cluster.'''

        if self.config.get('cluster', 'headers') in ['yes', 'true']:
            print 'URI Name'
        for uri, name, dom in self.listAllDomains():
            print uri, name

    def cmd_find(self, args):
        '''Locate a domain by name.'''

        for name in args:
            res = self.lookupByName(name)
            if res:
                uri, dom = res
                print dom.name(), uri
            else:
                print >>sys.stderr, '%s: not found' % name

    def cmd_hosts(self, args):
        '''List information for hosts in the cluster.'''

        if self.config.get('cluster', 'headers') in ['yes', 'true']:
            print ' '.join(('Name', 'Type', 'Arch', 'Mem', 'CPU', 'Domains'))
        for conn in self.connections():
            info = conn.getInfo()
            print ' '.join([str(x) for x in (conn.getHostname(),
                    conn.getType(),
                    info[0],
                    info[1],
                    info[2],
                    conn.numOfDomains())])

    def cmd_help(self, args):
        '''Dislay documentation for lvc subcommands.'''

        print 'lvc: libvirt cluster'
        print

        for fname in [attr for attr in dir(self) if attr.startswith('cmd_')]:
            cmd = fname[4:]
            func = getattr(self, fname)
            print '%s' % cmd
            print '  %s' % func.__doc__

        print

def parse_args():
    p = optparse.OptionParser()
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

    return cluster

if __name__ == '__main__':
    c = main()

