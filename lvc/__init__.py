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
        'selector'  : 'mem',
        }

class Cluster (object):

    def __init__ (self, config):
        self.config = config
        self.hosts = config.get('cluster', 'hosts').split()
        libvirt.registerErrorHandler(self.errorHandler, None)

    def errorHandler(self, ctx, error):
        pass

    def listAllHosts(self):
        for conn in self.connections():
            info = conn.getInfo()
            yield {
                    'conn': conn,
                    'uri': conn.getURI(),
                    'hostname': conn.getHostname(),
                    'type': conn.getType(),
                    'arch': info[0],
                    'memtotal': info[1],
                    'memavail': conn.getFreeMemory()/1024/1024,
                    'cpus': info[2],
                    'activeDomains': conn.numOfDomains(),
                    'definedDomains': conn.numOfDefinedDomains(),
                    }

    def listAllDomains(self):
        for host in self.listAllHosts():
            for domid in host['conn'].listDomainsID():
                dom = host['conn'].lookupByID(domid)
                yield {
                        'host': host,
                        'name': dom.name(),
                        'domain': dom,
                        }
                        
    def lookupByName(self, name):
        for host in self.listAllHosts():
            try:
                dom = host['conn'].lookupByName(name)
                return {
                        'host': host,
                        'name': dom.name(),
                        'domain': dom,
                        }
            except libvirt.libvirtError, detail:
                if detail.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                    continue
                else:
                    raise

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
        for dom in self.listAllDomains():
            print dom['host']['uri'], dom['name']

    def cmd_hosts(self, args):
        '''List information for hosts in the cluster.'''

        if self.config.get('cluster', 'headers') in ['yes', 'true']:
            print ' '.join(('Name', 'Type', 'Arch', 'MemTotal', 'MemAvail', 'CPU', 'Domains'))
        for host in self.listAllHosts():
            print ' '.join((str(host[x]) for x in (
                'hostname',
                'type',
                'memtotal',
                'memavail',
                'cpus',
                'activeDomains',
                )))

    def cmd_find(self, args):
        '''Locate a domain by name.'''

        for name in args:
            dom = self.lookupByName(name)
            if dom:
                print dom['host']['uri'], name
            else:
                print >>sys.stderr, '%s: not found' % name

    def cmd_select(self, args):
        selector = self.config.get('cluster', 'selector')
        selected = None

        for host in self.listAllHosts():
            if selected is None:
                selected = host
            elif selector == 'mem' and host['memavail'] > selected['memavail']:
                selected = host
            elif selector == 'packing' and (
                    host['activeDomains']/host['cpus'] >
                    selected['activeDomains']/selected['cpus']
                    ):
                selected = host

        print selected['uri']

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

if __name__ == '__main__':
    main()

