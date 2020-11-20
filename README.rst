****************************
Mopidy-TidalOAuth
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-TidalOAuth.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-TidalOAuth/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-TidalOAuth.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-TidalOAuth/
    :alt: Number of PyPI downloads

Tidal music service integration.



Installation
============

Install by running::

    pip install Mopidy-TidalOAuth

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

You need to set an ``oauth_port`` value and browse to ``http://MOPIDY_SERVER_IP:oauth_port`` web-page and do **ONCE** the OAuth Login Flow.

Please follow the information found on the web-page. You will be redirected to TIDAL service for authentication.

At the end of the process, credential autorefresh will be on indefinitely.

=====

Quality can be set to HI_RES (Master), LOSSLESS, HIGH or LOW.
Lossless quality (FLAC) requires Tidal HiFi Subscription.
For High and Low quality be sure to have installed gstreamer bad-plugins, for eg::

    sudo pacman -S gstreamer0.10-bad-plugins
    

This is mandatory to be able to play m4a streams.

Project resources
=================

- `Source code <https://github.com/quodrum-glas/mopidy-tidal>`_
- `Issue tracker <https://github.com/quodrum-glas/mopidy-tidal/issues>`_


Credits
=======

- Original author: `mones88 <https://github.com/mones88>`__
- Original author: `tehkillerbee <https://github.com/tehkillerbee>`__
- Current maintainer: `quodrumglas <https://github.com/quodrum-glas>`__
- `Contributors <https://github.com/quodrum-glas/mopidy-tidal/graphs/contributors>`_


Changelog
=========

v0.3.0
----------------------------------------
- Using updated tidal api for OAuth credentials
- HTTP server to assist with creating auto-refresh OAuth credentials
- Improved caching for much faster browsing experience


v0.2.3
----------------------------------------
- Fork from Mopidy-Tidal