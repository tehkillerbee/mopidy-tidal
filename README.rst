****************************
Mopidy-Tidal
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-Tidal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Tidal/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-Tidal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Tidal/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/mones88/mopidy-tidal/master.svg?style=flat
    :target: https://travis-ci.org/mones88/mopidy-tidal
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/mones88/mopidy-tidal/master.svg?style=flat
   :target: https://coveralls.io/r/mones88/mopidy-tidal
   :alt: Test coverage

Tidal music service integration.



Installation
============

Install by running::

    pip install --upgrade -e git+https://github.com/quodrum-glas/python-tidal.git#egg=python-tidal-0.6.7
    pip install --upgrade -e git+https://github.com/quodrum-glas/mopidy-tidal.git#egg=mopidy-tidal

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-Tidal to your Mopidy configuration file::

    [tidal]
    enabled = true
    token = ${X-Tidal-Token}  # /Android/data/com.aspiro.tidal/cache/okhttp found in some of the files ending .0
    oauth = /var/lib/mopidy/tidal.cred # or any location where credentials to be stored after going through OAuth Flow
    oauth_port = 8000 - 9999  # Optional, for HTTP server to assist in creating oauth credentials stored above.
    image_search = false      # image location should be cached from browsing. Set 'true' to search if cache item not found
    quality = LOSSLESS        # with Android token this can be HI_RES (Master)


Quality can be set to HI_RES (Master), LOSSLESS, HIGH or LOW.
Lossless quality (FLAC) requires Tidal HiFi Subscription.
For High and Low quality be sure to have installed gstreamer bad-plugins, for eg::

    sudo pacman -S gstreamer0.10-bad-plugins
    

This is mandatory to be able to play m4a streams.

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

v0.3.0
----------------------------------------
- Using updated tidal api for OAuth credentials
- HTTP server to assist with creating auto-refresh OAuth credentials
- Improved caching for much faster browsing experience


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
