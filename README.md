# Mopidy-Tidal

[![Latest PyPI version](https://img.shields.io/pypi/v/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![Number of PyPI downloads](https://img.shields.io/pypi/dm/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![codecov](https://codecov.io/gh/tehkillerbee/mopidy-tidal/branch/master/graph/badge.svg?token=cTJDQ646wy)](https://codecov.io/gh/tehkillerbee/mopidy-tidal)

Mopidy Extension for Tidal music service integration.

### Changelog
Find the latest changelog [here](CHANGELOG.md)

### Contributions
- Current maintainer: [tehkillerbee](https://github.com/tehkillerbee)
- Original author: [mones88](https://github.com/mones88)
- [Contributors](https://github.com/tehkillerbee/mopidy-tidal/graphs/contributors)

Questions related to Mopidy-Tidal, feature suggestions, bug reports and Pull Requests are very welcome.

If you are experiencing playback issues unrelated to this plugin, please report this to the Mopidy-Tidal issue tracker and/or check [Python-Tidal/Tidalapi repository](https://github.com/tamland/python-tidal) for relevant issues.

### Development guidelines
Please refer to [this document](DEVELOPMENT.md) to get you started.

## Getting started
First install and configure Mopidy as per the instructions listed [here](https://docs.mopidy.com/en/latest/installation/). It is encouraged to install Mopidy as a systemd service, as per the instructions listed [here](https://docs.mopidy.com/en/latest/running/service/). 

After installing Mopidy, you can now proceed installing the plugins that you require, including Mopidy-Tidal. :
```
sudo pip3 install Mopidy-Tidal
```

Poetry can also be used to install mopidy-tidal and its dependencies.
```
cd <mopidy-tidal source root>
poetry install
```

##### Note: Make sure to install the Mopidy-Tidal plugin in the same python venv used by your Mopidy installation. Otherwise, the plugin will NOT be detected.

### Install from latest sources
In case you are upgrading your Mopidy-Tidal installation from the latest git sources, make sure to do a force upgrade from the source root (remove both mopidy-tidal and python-tidal), followed by a (service) restart.
```
cd <mopidy-tidal source root>
sudo pip3 uninstall mopidy-tidal
sudo pip3 uninstall tidalapi
sudo pip3 install .
sudo systemctl restart mopidy
```

## Dependencies
### Python

Released versions of Mopidy-Tidal have the same requirement as the Mopidy
version they depend on.  Development code may depend on unreleased features.
At the time of writing we require python >= 3.9 in anticipation of mopidy 3.5.0.

### Python-Tidal
Mopidy-Tidal requires the Python-Tidal API (tidalapi) to function. This is usually installed automatically when installing Mopidy-Tidal.
In some cases, Python-Tidal stops working due to Tidal changing their API keys.

When this happens, it will usually be necessary to upgrade the Python-Tidal API plugin manually
```
sudo pip3 install --upgrade tidalapi
```

After upgrading Python-Tidal/tidalapi, it will often be necessary to delete the existing json file and restart mopidy.
The file is usually stored in `/var/lib/mopidy/tidal/tidal-oauth.json`, depending on your system configuration.

### GStreamer
When using High and Low quality, be sure to install gstreamer bad-plugins, e.g.:
```
sudo apt-get install gstreamer1.0-plugins-bad
```
This is mandatory to be able to play m4a streams.

## Plugin Configuration

Before starting Mopidy, you must add configuration for Mopidy-Tidal to your Mopidy configuration file, if it is not already present.

Run `sudo mopidyctl config` to see the current effective config used by Mopidy

The configuration is usually stored in `/etc/mopidy/mopidy.conf`, depending on your system configuration. Add the configuration listed below in the respective configuration file:
```
[tidal]
enabled = true
quality = LOSSLESS
#client_id =
#client_secret =
#playlist_cache_refresh_secs = 0
#lazy = false
```

Restart the Mopidy service after adding the Tidal configuration
```
sudo systemctl restart mopidy
```

### Plugin configuration
The plugin configuration is usually set in your mopidy configuration:
```
[tidal]
enabled = true
quality = LOSSLESS
#playlist_cache_refresh_secs = 0
lazy = true
login_method = HACK
#client_id =
#client_secret =
```
* **quality:** Set to either HI_RES_LOSSLESS, LOSSLESS, HIGH or LOW. Make sure to use a quality level supported by your current subscription

    * Note: `HI_RES_LOSSLESS` quality  (i.e. Max quality) requires a Tidal HiFi Plus subscription, while `LOSSLESS` quality (i.e. HiFi lossless) requires a HiFi subscription.

* **playlist_cache_refresh_secs (Optional):** Tells if (and how often) playlist
content should be refreshed upon lookup.
  * `0` (default): The default value (`0`) means that playlists won't be refreshed after the
  extension has started, unless they are explicitly modified from mopidy.
  * `>0`: A non-zero value expresses for how long (in seconds) a cached playlist is
  considered valid. For example, a value of `300` means that the cached snapshot
  of a playlist will be used if a new `lookup` occurs within 5 minutes from the
  previous one, but the playlist will be re-loaded via API if a lookup request
  occurs later.

  The preferred setting for this value is a trade-off between UI responsiveness
and responsiveness to changes. If you perform a lot of playlist changes from
other clients and you want your playlists to be instantly updated on mopidy,
then you may choose a low value for this setting, albeit this will result in
longer waits when you look up a playlist, since it will be fetched from
upstream most of the times. If instead you don't perform many playlist
modifications, then you may choose a value for this setting within the range of
hours - or days, or even leave it to zero so playlists will only be refreshed
when mopidy restarts. This means that it will take longer for external changes
to be reflected in the loaded playlists, but the UI will be more responsive
when playlists are looked up. A value of zero makes the behaviour of
`mopidy-tidal` quite akin to the current behaviour of `mopidy-spotify`.

* **lazy (Optional):**: Whether to connect lazily, i.e. when required, rather than
at startup.
  * `false` (default): Lazy mode is off by default for backwards compatibility and to make the first login easier (since mopidy will not block in lazy mode until you try to access Tidal).
  * `true`: Mopidy-Tidal will only try to connect when something
  tries to access a resource provided by Tidal.  
  
  Since failed connections due to
  network errors do not overwrite cached credentials (see below) and Mopidy
  handles exceptions in plugins gracefully, lazy mode allows Mopidy to continue to
  run even with intermittent or non-existent network access (although you will
  obviously be unable to play any streamed music if you cannot access the
  network).  When the network comes back Mopidy will be able to play tidal content
  again.  This may be desirable on mobile internet connections, or when a server
  is used with multiple backends and a failure with Tidal should not prevent
  other services from running.
* **login_method (Optional):**: This setting configures the OAuth login process. 
  * `BLOCK` (block): The user is REQUIRED to complete the OAuth login flow, otherwise mopidy will hang.
  * `HACK`: Mopidy will start as usual but the user will be prompted to complete the OAuth login flow. The link is provided through a dummy track (i.e. HACK)
* **client_id, _secret (Optional):**: Tidal API `client_id`, `client_secret` can be overridden by the user if necessary.

### OAuth Flow
The first time you use the plugin, you will have to use the OAuth flow to login.:

1. After restarting the Mopidy server, check the latest systemd logs and find a line like:
```
journalctl -u mopidy | tail -10
...
Visit link.tidal.com/AAAAA to log in, the code will expire in 300 seconds.
```
2. Visit the link to connect the mopidy tidal plugin to your Tidal account.

The OAuth session will be reloaded automatically when Mopidy is restarted. It
will be necessary to perform these steps again if/when the session expires or if
the json file is moved/deleted.

##### Note: Login process is a **blocking** action, so Mopidy + Web interface will stop loading until you approve the application.

If for some reason loading cached credentials fails, `mopidy-tidal` will restart
the oauth flow (potentially blocking mopidy).  If connection failed for a
network error and this new connection also fails, your cached credentials will
not be overwritten.  There is, however, a potential race condition where the
network comes back online after a failed connection and `mopidy-tidal`
unnecessarily requests new credentials.  This bug has never been reported in the
wild and is only mildly annoying, whereas any logic to detect it (for instance
by inspecting the specific failure from `python-tidal`) would probably be more
fragile.