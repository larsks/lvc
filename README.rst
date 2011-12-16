==========================
lvc: libvirt cluster tools
==========================

lvc provides a set of commands for interacting with a cluster
of libvirt-based hosts.

Synopsis
========

::

  lvc [ --headers ] [ --config <config file> ] <command> [ <arguments> ... ]

Options
=======

``--headers``, ``-H``
  Display column headers on output.
``--config`` *configfile*, ``-f`` *configfile*
  Read configuration from *configfile* instead of
  ``/etc/libvirt/cluster.conf``.

Commands
========

``find`` *name*
  Locate a domain by name (supports glob-style patterns).
``help``
  Dislay documentation for lvc subcommands.
``hosts`` [ ``--uris`` ]
  Display information for hosts in the cluster.
``list``
  List all domains running on the cluster.
``select`` [ ``-pm`` ]
  Select a host based on memory or virtual instance/CPU ratio.

Configuration file format
=========================

The configuration file is an INI-format file (parsed with Python's
ConfigParser moduel).  The file must contain one ``cluster`` section, and
may contain one or more ``auth`` sections.

cluster
-------

``hosts``
  A list of libvirt URIs identifying the hosts that comprise the cluster.
``headers``
  If ``true``, display column headers in ``list``, ``find``, and ``host``
  commands.
``selector``
  Default selector for the ``select`` command.  One of ``mem`` or
  ``packing``.

Example
~~~~~~~

::

  [cluster]

  hosts = qemu:///system
          qemu+ssh://anotherhost/system

auth
----

An ``auth`` section defines authentication credentials for connections that
require authentication.  The section is named ``auth <uri>``, where *<uri>*
is a URI from the ``hosts`` key in the ``cluster`` section.

``username``
  Username for the connection.
``password``
  Password for the connection.

Example
~~~~~~~

::

  [cluster]

  hosts = esx://anotherhost/?no_verify=1

  [auth esx://anotherhost/?no_verify=1]

  username = root
  password = secret

Examples
========

Getting a list of hosts::

  # lvc hosts
  arc-vm-2.int.seas.harvard.edu QEMU 258020 156710 48 14
  arc-vm-3.int.seas.harvard.edu QEMU 258020 110198 48 37
  arc-vm-4.int.seas.harvard.edu QEMU 258020 64132 48 96
  arc-vm-5.int.seas.harvard.edu QEMU 64551 59647 16 1

Find a host using a wildcard pattern::

  # lvc find centos*
  qemu+ssh://arc-vm-2/system centos-6-dev-0

Find the host with the most available memory::

  # lvc select
  qemu+ssh://arc-vm-2/system

You can use ``lvc select`` in a call to ``virt-install`` to select
your target host::

  # virt-install --connect `lvc select` -n myNewHost ...

Author
======

lvc was written by Lars Kellogg-Stedman <lars@seas.harvard.edu>.

License
=======

See the file ``LICENSE.txt`` distributed with this software.

