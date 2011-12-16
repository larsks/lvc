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

