katello-rapidnode
=================

`katello_rapidnode.py` is a script which automates the process of setting up
one or more systems as capsules.

Setup
-----

A Satellite 6 system must be available, and the following should be true:

1. A Red Hat Subscription is active. In other words, an appropriate manifest
   file has been downloaded from
   [access.redhat.com](https://access.redhat.com/home) and uploaded to the
   Satellite.
2. Repositories containing capsule packages are enabled and synced. The
   following are mandatory:

   * Red Hat Enterprise Linux X Server RPMs
   * Red Hat Satellite Y for RHEL X Server RPMs

   The enabled and synced repositories should match the system the capsule is
   being installed on. For example, the "Red Hat Enterprise Linux 6 Server RPMs
   x86\_64 6.6" repository should be enabled if a capsule is being installed on
   a RHEL 6.6 x86\_64 system.
3. A content view exists and has been published. It should provide the
   repositories from the previous step.
4. An activation key exists. It should provide the content view from the
   previous step. (FIXME: necessary?)

`katello_rapidnode.py` can be run on any machine where:

* Python 2.7 or 3.x is installed. The Python development packages should also
  be installed, or else the extra modules listed in `requirements.txt` may not
  compile correctly. (On RPM-based systems, try `yum install python-devel`.)
* The modules listed in `requirements.txt` are installed. These modules may be
  installed via any of the usual methods: your package manager, manually, or
  with a PyPi helper such as easy\_install or pip. (On many systems, `pip
  install -r requirements.txt` will work.)
* The `katello_rapidnode.ini` file is present and populated. The
  `katello_rapidnode.sample.ini` file serves as a template.
* (optional) The `myrepofile.repo` file is present and populated. The
  `myrepofile.sample.repo` file serves as a template.

Usage
-----

Execute the `katello_rapidnode.py` script. The script will configure the
`[servers]` listed in `katello_rapidnode.ini` via SSH.

To Contribute
-------------

Submitting a pull request on GitHub is an easy way to contribute. Please check
your code with flake8 and pylint before submitting any contributions:

    flake8 .
    pylint *.py
    ./test.py

These tools are listed in `requirements-optional.txt`, which makes it easy to
install them:

    pip install -r requirements-optional.txt
