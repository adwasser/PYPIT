.. highlight:: rest
	       
*************	   
Install hacks
*************


GSL installations
=================

If you don't want to install GSL through Anaconda, you can use `brew <http://brew.sh/>`_ (on Mac OSX)::

  brew install gsl

in which case the ``GSL_PATH`` variable should be set to ``/usr/local/Cellar/gsl/1.16/``, where ``1.16`` might have to
be replaced with whatever version number you have installed.

On Linux systems, your distribution's packagage manager (e.g., yum/dnf for Fedora, apt-get for Ubuntu) should be able to
install gsl::

  sudo dnf install gsl

For this particular case, the ``GSL_PATH`` could just be set to ``/usr/lib/``.

Local installation
==================

If you don't have super user privileges on your machine, and you wish to use pip to install python packages, you can use
the ``--user`` flag for pip, e.g.::

  pip install --user package


Global installation with sudo
=============================

Depending on your python installation, you may need to call setup with sudo::

  sudo python setup.py install

Should this fail with a warning along the lines of::

  Traceback (most recent call last):
    File "setup.py", line 69, in <module>
      include_gsl_dir = os.getenv('GSL_PATH')+'/include/'
  TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'

Then you should make sure that sudo can find the environment variable ``GSL_PATH``.  This can be done as::

  sudo -E python setup.py install



