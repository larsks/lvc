#!/usr/bin/python

import sys
import optparse
import fnmatch
import textwrap
import re

import libvirt

# Used to transtate state information from dom.info().
domainStates = {
        libvirt.VIR_DOMAIN_RUNNING  : 'running',
        libvirt.VIR_DOMAIN_BLOCKED  : 'idle',
        libvirt.VIR_DOMAIN_PAUSED   : 'paused',
        libvirt.VIR_DOMAIN_SHUTDOWN : 'shutdown',
        libvirt.VIR_DOMAIN_SHUTOFF  : 'off',
        libvirt.VIR_DOMAIN_CRASHED  : 'crashed',
        libvirt.VIR_DOMAIN_NOSTATE  : 'nostate',
        }

# Columns output by "list" and "find" commands.
domainColumns = [ 'name', 'persist', 'state' ]

# Columns output by "hosts" command.
hostColumns = [ 'type', 'arch',
        'memtotal', 'memavail', 'cpus',
        'activeDomains' ]

class Cluster (object):

    def __init__ (self, config):
        self.config = config
        self.hosts = config.get('cluster', 'hosts').split()
        libvirt.registerErrorHandler(self.errorHandler, None)

    def errorHandler(self, ctx, error):
        '''This is a null error handler used to keep libVirt quiet.'''
        pass

    def authCallback(self, credentials, data):
        '''Libvirt authentication callback.'''

        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                if self.config.has_option('auth %s' % data, 'username'):
                    credential[4] = self.config.get('auth %s' % data, 'username')
                else:
                    credential[4] = credential[3]
            elif credential[0] == libvirt.VIR_CRED_NOECHOPROMPT:
                if self.config.has_option('auth %s' % data, 'password'):
                    credential[4] = self.config.get('auth %s' % data, 'password')
            else:
                return -1

        return 0

    def listAllHosts(self):
        '''Return an iterator over all the hosts in the cluster.'''
        for conn in self.connections():
            info = conn.getInfo()

            # This is an ugly hack to compensate for the fact the the
            # "architecture" parameter provided by the esx:// driver is
            # actually the processor "model name", and unsuitable for
            # consumption by awk, etc., due to lots of embedded whitespace.
            # We take the first string of alphanumeric characters and
            # discard the rest.
            arch = info[0]
            mo = re.match('(\w+)', arch)
            arch = mo.group(1)

            yield {
                    'conn': conn,
                    'uri': conn.getURI(),
                    'hostname': conn.getHostname(),
                    'type': conn.getType(),
                    'arch': arch,
                    'memtotal': info[1],
                    'memavail': conn.getFreeMemory()/1024/1024,
                    'cpus': info[2],
                    'activeDomains': conn.numOfDomains(),
                    'definedDomains': conn.numOfDefinedDomains(),
                    }

    def domainInfo(self, host, dom):
        '''Return a dictionary describing a domain.'''
        info = dom.info()

        return {
                'host': host,
                'name': dom.name(),
                'domain': dom,
                'persist': dom.isPersistent() and 'y' or 'n',
                'state': domainStates[info[0]],
                }

    def listAllDomains(self):
        '''Return an iterator over all active domains on all hosts.'''
        for host in self.listAllHosts():
            for domid in host['conn'].listDomainsID():
                dom = host['conn'].lookupByID(domid)
                yield self.domainInfo(host, dom)
                        
    def lookupByPattern(self, name):
        for dom in self.listAllDomains():
            if fnmatch.fnmatch(dom['name'], name):
                yield dom

    def lookupByName(self, name):
        for host in self.listAllHosts():
            try:
                dom = host['conn'].lookupByName(name)
                yield self.domainInfo(host, dom)
            except libvirt.libvirtError, detail:
                if detail.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                    continue
                else:
                    raise

    def lookup(self, name):
        '''Lookup hosts by name or, if name contains a '*', by pattern.'''
        if '*' in name:
            return self.lookupByPattern(name)
        else:
            return self.lookupByName(name)

    def connections(self):
        '''Return an iterator over connections to cluster hosts.'''
        for uri in self.hosts:
            try:
                auth = [
                        [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_NOECHOPROMPT],
                        self.authCallback,
                        uri]
                yield libvirt.openAuth(uri, auth, 0)
            except libvirt.libvirtError, detail:
                print >>sys.stderr, 'ERROR: %s: %s' % (
                        uri, detail.get_error_message())
                continue

    def dispatch(self, cmd, args):
        '''Dispatch a command to the appropriate handler.'''
        if hasattr(self, 'cmd_%s' % cmd):
            return getattr(self, 'cmd_%s' % cmd)(args)
        else:
            raise NotImplementedError(cmd)

    def printDomains(self, iter):
        if self.config.get('cluster', 'headers') == 'true':
            print 'URI', ' '.join(domainColumns)

        empty=True
        for dom in iter:
            empty=False
            print dom['host']['uri'], ' '.join((
                dom[x] for x in domainColumns))

        return not empty

    def cmd_list(self, args):
        '''List all domains running on the cluster.'''
        self.printDomains(self.listAllDomains())
        return 0

    def cmd_find(self, args):
        '''Locate domains by name (supports glob-style patterns).'''
        foundSomething = False
        for dom in [self.lookup(name) for name in args]:
            if self.printDomains(dom):
                foundSomething = True

        if not foundSomething:
            print >>sys.stderr, 'Nothing found.'
            return 1

    def hosts_parse(self, args):
        p = optparse.OptionParser()
        p.add_option('-u', '--uris', action='store_true')
        return p.parse_args(args)

    def cmd_hosts(self, args):
        '''Display information for all hosts in the cluster.  Use
        --uris to display connection strings instead of hostnames.'''

        opts, args = self.hosts_parse(args)

        if opts.uris:
            namevar = 'uri'
        else:
            namevar = 'hostname'

        if self.config.get('cluster', 'headers') == 'true':
            print namevar, ' '.join(hostColumns)
        for host in self.listAllHosts():
            print ' '.join((str(host[x]) for x in [namevar] + hostColumns))

        return 0

    def select_parse(self, args, selector=None):
        p = optparse.OptionParser()
        p.add_option('-m', '--mem', action='store_const',
                const='mem', dest='selector')
        p.add_option('-p', '--packing', action='store_const',
                const='packing', dest='selector')
        p.add_option('-t', '--type',
                help='Restrict hosts to a specific hypervisor type.')

        p.set_defaults(selector=selector)
        return p.parse_args(args)

    def cmd_select(self, args):
        '''Return a single URI suitable for deploying a new virtual
        instance based on the value of the 'selector'.  If selector == mem
        (-m), returns the host with the most available free memory.  If
        selector == packing (-p), returns the host with the lowest active
        domains/cpus ratio.'''

        selected = None

        opts, args = self.select_parse(args,
                selector=self.config.get('cluster', 'selector'))

        for host in self.listAllHosts():
            if opts.type and host['type'].lower() != opts.type.lower():
                continue

            if selected is None:
                selected = host
            elif opts.selector == 'mem' and host['memavail'] > selected['memavail']:
                selected = host
            elif opts.selector == 'packing' and (
                    host['activeDomains']/host['cpus'] <
                    selected['activeDomains']/selected['cpus']
                    ):
                selected = host

        if selected:
            print selected['uri']
        else:
            print >>sys.stderr, 'Nothing selected by filters.'
        return 0

    def cmd_help(self, args):
        '''Dislay documentation for lvc subcommands.'''

        print 'lvc: libvirt cluster'
        print

        for fname in [attr for attr in dir(self) if attr.startswith('cmd_')]:
            cmd = fname[4:]
            func = getattr(self, fname)
            print '%s' % cmd
            print textwrap.fill(func.__doc__,
                    initial_indent='  ',
                    subsequent_indent='  ')

        print
        return 0


