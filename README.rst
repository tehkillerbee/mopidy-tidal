****************************
Mopidy-Tidal
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-Tidal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Tidal/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-Tidal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Tidal/
    :alt: Number of PyPI downloads

Tidal music service integration.

Installation
============

Install by running::

    pip install Mopidy-Tidal
    or
    pip3 install Mopidy-Tidal

In case you are upgrading your Mopidy-Tidal installation from the latest git sources, make sure to do a force upgrade from the source root::

    sudo python3 setup.py install --force




Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-Tidal to your Mopidy configuration file::

    [tidal]
    enabled = true
    username = YOUR_TIDAL_USERNAME
    password = YOUR_TIDAL_PASSWORD
    quality = LOSSLESS


Quality can be set to LOSSLESS, HIGH or LOW. Hi_RES(master) is currently not supported.
Lossless quality (FLAC) requires Tidal HiFi Subscription.

For High and Low quality be sure to have installed gstreamer bad-plugins, eg. ::

    sudo apt-get install gstreamer1.0-plugins-bad

This is mandatory to be able to play m4a streams.

OAuth Flow
----------

Using the new OAuth flow, you now have to visit a link to connect the mopidy app to your login.
When you restart the Mopidy server, check the latest systemd logs and find a line like::

    journalctl -u mopidy | tail -5
    ...
    Visit link.tidal.com/AAAAA to log in, the code will expire in 300 seconds``

Go to that link in your browser, approve it, and that should be it. Note that this is a **blocking** action, so Mopidy will not load until you approve the application.
The OAuth session will be reloaded automatically when Mopidy is restarted. However, it will be necessary to perform these steps again if/when the session expires.

Project resources
=================

- `Source code <https://github.com/tehkillerbee/mopidy-tidal>`_
- `Issue tracker <https://github.com/tehkillerbee/mopidy-tidal/issues>`_


Credits
=======

- Original author: `mones88 <https://github.com/mones88>`__
- Current maintainer: `tehkillerbee <https://github.com/tehkillerbee>`__
- `Contributors <https://github.com/tehkillerbee/mopidy-tidal/graphs/contributors>`_


Changelog
=========

v0.2.5
----------------------------------------
- Reload existing OAuth session on Mopidy restart
- Added OAuth login support from tidalapi (thanks to greggilbert)

v0.2.4
----------------------------------------
- Added track caching (thanks to MrSurly and kingosticks)

v0.2.3
----------------------------------------
- fixed python 3 compatibility issues
- Change dependency tidalapi4mopidy back to tidalapi (thanks to stevedenman)

v0.2.2
----------------------------------------
- added support browsing of favourite tracks, moods, genres and playlists (thanks to SERVCUBED)


v0.2.1
----------------------------------------
- implemented get_images method
- updated tidal's api key


v0.2.0
----------------------------------------
- playlist support (read-only)
- implemented artists lookup
- high and low quality streams should now work correctly
- cache search results (to be improved in next releases)

v0.1.0
----------------------------------------

- Initial release.
