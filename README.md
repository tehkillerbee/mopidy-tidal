# Mopidy-Tidal

[![Latest PyPI version](https://img.shields.io/pypi/v/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![Number of PyPI downloads](https://img.shields.io/pypi/dm/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![codecov](https://codecov.io/gh/tehkillerbee/mopidy-tidal/branch/master/graph/badge.svg?token=cTJDQ646wy)](https://codecov.io/gh/tehkillerbee/mopidy-tidal)

Mopidy Extension for Tidal music service integration.

## Installation
First install and configure Mopidy as per the instructions listed [here](https://docs.mopidy.com/en/latest/installation/). It is encouraged to install Mopidy as a systemd service, as per the instructions listed [here](https://docs.mopidy.com/en/latest/running/service/). 

After installing Mopidy, you can now proceed installing the plugins, including Mopidy-Tidal. :
```
sudo pip3 install Mopidy-Tidal
```

##### Note: Make sure to install the Mopidy-Tidal plugin in the same python venv used by your Mopidy installation. Otherwise, the plugin will NOT be detected.

### Install from latest sources
In case you are upgrading your Mopidy-Tidal installation from the latest git sources, make sure to do a force upgrade from the source root, followed by a (service) restart.
```
cd <mopidy-tidal source root>
sudo pip3 uninstall mopidy-tidal
sudo pip3 install .
sudo systemctl restart mopidy
```

## Dependencies
### Python

Mopidy-Tidal requires python >= 3.7.  3.7 is supported in theory as many people
are still using it on embedded devices, but our test suite does not currently
have 100% coverage under 3.7 (PRs to fix this are welcome!).  Mopidy-Tidal is
fully tested on python >= 3.8.

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
When using High and Low quality, be sure to install gstreamer bad-plugins, eg.:
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
```

Restart the Mopidy service after adding the Tidal configuration
```
sudo systemctl restart mopidy
```

### Parameters

**Quality:** Set to LOSSLESS, HIGH or LOW. Hi_RES(master) is currently not supported.
Lossless quality (FLAC) requires Tidal HiFi Subscription.

**client_id, _secret (Optional):**: Tidal API `client_id`, `client_secret` can be overridden by the user if necessary.

**playlist_cache_refresh_secs (Optional):** Tells if (and how often) playlist
content should be refreshed upon lookup.

The default value (`0`) means that playlists won't be refreshed after the
extension has started, unless they are explicitly modified from mopidy.

A non-zero value expresses for how long (in seconds) a cached playlist is
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

## OAuth Flow

Using the OAuth flow, you have to visit a link to connect the mopidy app to your Tidal account.

1. When you restart the Mopidy server, check the latest systemd logs and find a line like:
```
journalctl -u mopidy | tail -10
...
Visit link.tidal.com/AAAAA to log in, the code will expire in 300 seconds.
```
2. Go to that link in your browser, approve it, and that should be it.

The OAuth session will be reloaded automatically when Mopidy is restarted. It will be necessary to perform these steps again if/when the session expires or if the json file is moved.

##### Note: Login process is a **blocking** action, so Mopidy + Web interface will NOT load until you approve the application.

## Test Suite
Mopidy-Tidal has a test suite which currently has 100% coverage.  Ideally
contributions would come with tests to keep this coverage up, but we can help in
writing them if need be.

To run the test suite you need to install `pytest`, `pytest-mock` and
`pytest-cov` inside your venv:

```bash
pip3 install -r test_requirements.txt
```

You can then run the tests:

```bash
pytest tests/ -k "not gt_3_10" --cov=mopidy_tidal --cov-report=html
--cov-report=term-missing --cov-branch
```

substituting the correct python version (e.g. `-k "not gt_3.8"`).  This is
unlikely to be necessary beyond 3.9 as the python language has become very
standard.  It's only really needed to exclude a few tests which check that
dict-like objects behave the way modern dicts do, with `|`.

If you are on *nix, you can simply run:

```bash
make test
```

Currently the code is not very heavily documented.  The easiest way to see how
something is supposed to work is probably to have a look at the tests.

### Code Style
Code should be formatted with `isort` and `black`:

```bash
isort --profile=black mopidy_tidal tests
black mopidy_tidal tests
```

if you are on *nix you can run:

```bash
make format
```

The CI workflow will fail on linting as well as test failures.

## Contributions
Source contributions, suggestions and pull requests are very welcome.

If you are experiencing playback issues unrelated to this plugin, please report this to the Mopidy-Tidal issue tracker and/or check [Python-Tidal/Tidalapi repository](https://github.com/tamland/python-tidal) for relevant issues.

### Contributor(s)
- Current maintainer: [tehkillerbee](https://github.com/tehkillerbee)
- Original author: [mones88](https://github.com/mones88)
- [Contributors](https://github.com/tehkillerbee/mopidy-tidal/graphs/contributors)


### Project resources
- [Source code](https://github.com/tehkillerbee/mopidy-tidal)
- [Issue tracker](https://github.com/tehkillerbee/mopidy-tidal/issues)
- [Python-Tidal repository](https://github.com/tamland/python-tidal)
- [Python-Tidal issue tracker](https://github.com/tamland/python-tidal/issues)

### Changelog

#### v0.3.2
- Implemented a configurable `playlist_cache_refresh_secs`
- Replace colons in cache filenames with hyphens to add FAT32/NTFS compatibility

(Thanks [BlackLight](https://github.com/BlackLight) for the above PRs)

#### v0.3.1
- Added support for tidalapi 0.7.x. Tidalapi >=0.7.x is now required.
- Added support for Moods, Mixes, track/album release date.
- Speed, cache improvements and Iris bugfixes.
- Overhauled Test suite
- Support for playlist editing

(Major thanks [BlackLight](https://github.com/BlackLight) and [2e0byo](https://github.com/2e0byo) for the above improvements and all testers involved)

#### v0.2.8
- Major caching improvements to avoid slow intialization at startup. Code cleanup, bugfixes and refactoring (Thanks [BlackLight](https://github.com/BlackLight), [fmarzocca](https://github.com/fmarzocca))
- Reduced default album art, author and track image size.
- Improved Iris integration

#### v0.2.7
- Use path extension for Tidal OAuth cache file
- Improved error handling for missing images, unplayable albums
- Improved playlist browsing

#### v0.2.6
- Improved reliability of OAuth cache file generation.
- Added optional client_id & client_secret to [tidal] in mopidy config (thanks Glog78)
- Removed username/pass, as it is not needed by OAuth (thanks tbjep)

#### v0.2.5
- Reload existing OAuth session on Mopidy restart
- Added OAuth login support from tidalapi (thanks to greggilbert)

#### v0.2.4
- Added track caching (thanks to MrSurly and kingosticks)

#### v0.2.3
- fixed python 3 compatibility issues
- Change dependency tidalapi4mopidy back to tidalapi (thanks to stevedenman)

#### v0.2.2
- added support browsing of favourite tracks, moods, genres and playlists (thanks to SERVCUBED)

#### v0.2.1
- implemented get_images method
- updated tidal's api key

#### v0.2.0
- playlist support (read-only)
- implemented artists lookup
- high and low quality streams should now work correctly
- cache search results (to be improved in next releases)

#### v0.1.0
- Initial release.
