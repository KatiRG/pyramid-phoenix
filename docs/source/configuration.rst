.. _configuration:

Configuration
=============

You can configure Phoenix by editing ``custom.cfg`` in the Phoenix source folder:

.. code:: sh

   $ cd pyramid-phoenix
   $ vim custom.cfg
   $ cat custom.cfg

.. code:: ini

   [settings]
   hostname = localhost
   http-port = 8081
   https-port = 8443
   log-level = INFO
   # run 'make passwd' and add password here
   phoenix-password = sha256:#######################
   esgf-search-url = http://example.org/esg-search
   wps-url = http://localhost:8091/wps
   # register at github: https://github.com/settings/applications/new 
   github-consumer-key = ########################
   github-consumer-secret = ############################

By default Phoenix runs on localhost. The HTTP port 8081 is redirected to the HTTPS port 8443.
If you want to use a different hostname/port then edit the default values in ``custom.cfg``::

   [settings]
   hostname = localhost
   http-port = 8081
   https-port = 8443

To be able to login with the ``phoenix`` admin user you need to create a password. For this run:

.. code:: sh

   $ make passwd


Add the password hash to ``phoenix-password``:

.. code:: ini

   [settings]
   # run 'make passwd' and add password here
   phoenix-password = sha256:#######################

To activate the GitHub login for external users you need to configure a GitHub application key for your Phoenix web application:

.. code:: python

   [settings]
   # register at github: 
   github-consumer-key = ########################
   github-consumer-secret = ############################

See the `GitHub Settings <https://github.com/settings/applications/new>`_ on how to generate the application key for Phoenix.

If you want to use a different Malleefowl WPS service then change the ``wps-url`` value::

   [settings]
   wps-url = http://localhost:8091/wps

If you want to use a differnet ESGF index service then change the ``esgf-search-url`` value::

   [settings]
   esgf-search-url = http://example.org/esg-search

After any change to your ``custom.cfg`` you **need** to run ``make install`` again and restart the ``supervisor`` service::

  $ make install
  $ make restart
