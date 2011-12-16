#!/usr/bin/python

import sys
import optparse
import libvirt
import fnmatch

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
                        
    def lookupByPattern(self, name):
        for dom in self.listAllDomains():
            if fnmatch.fnmatch(dom['name'], name):
                return dom

    def lookupByName(self, name):
        if '*' in name:
            return self.lookupByPattern(name)

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

    def cmd_hosts_parse(self, args):
        p = optparse.OptionParser()
        p.add_option('-u', '--uris', action='store_true')
        return p.parse_args(args)

    def cmd_hosts(self, args):
        '''List information for hosts in the cluster.'''

        opts, args = self.cmd_hosts_parse(args)

        if self.config.get('cluster', 'headers') in ['yes', 'true']:
            print ' '.join(('Name', 'Type', 'Arch', 'MemTotal', 'MemAvail', 'CPU', 'Domains'))
        for host in self.listAllHosts():
            if opts.uris:
                namevar = 'uri'
            else:
                namevar = 'hostname'

            print ' '.join((str(host[x]) for x in (
                namevar,
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
                print dom['host']['uri'], dom['name']
            else:
                print >>sys.stderr, '%s: not found' % name

    def cmd_select_parse(self, args, selector=None):
        p = optparse.OptionParser()
        p.add_option('-m', '--mem', action='store_const',
                const='mem', dest='selector')
        p.add_option('-p', '--packing', action='store_const',
                const='packing', dest='selector')

        p.set_defaults(selector=selector)
        return p.parse_args(args)

    def cmd_select(self, args):
        '''Return a single URI suitable for deploying a new
        virtual instance based on the value of the 'selector'.
        If selector == mem, returns the host with the most available 
        free memory.  If selector == packing, returns the host with the
        lowest active domains/cpus ratio.'''

        selected = None

        opts, args = self.cmd_select_parse(args,
                selector=self.config.get('cluster', 'selector'))

        for host in self.listAllHosts():
            if selected is None:
                selected = host
            elif opts.selector == 'mem' and host['memavail'] > selected['memavail']:
                selected = host
            elif opts.selector == 'packing' and (
                    host['activeDomains']/host['cpus'] <
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

