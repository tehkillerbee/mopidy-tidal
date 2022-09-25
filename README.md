# Mopidy-Tidal

[![Latest PyPI version](https://img.shields.io/pypi/v/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![Number of PyPI downloads](https://img.shields.io/pypi/dm/Mopidy-Tidal.svg?style=flat)](https://github.com/tehkillerbee/mopidy-tidal)
[![codecov](https://codecov.io/gh/tehkillerbee/mopidy-tidal/branch/master/graph/badge.svg?token=cTJDQ646wy)](https://codecov.io/gh/tehkillerbee/mopidy-tidal)

Mopidy Extension for Tidal music service integration.

## Installation

Install by running::
```
pip3 install Mopidy-Tidal
```

In case you are upgrading your Mopidy-Tidal installation from the latest git sources, make sure to do a force upgrade from the source root, followed by a restart
```
cd <source root>
sudo pip3 uninstall mopidy-tidal
sudo pip3 install .
```

## Dependencies
### Python-Tidal
Mopidy-Tidal requires the Python-Tidal API to function. This is usually installed automatically.
In some cases, Python-Tidal stops working due to Tidal changing their API keys.

When this happens, it will usually be necessary to upgrade the Python-Tidal API plugin manually
```
sudo pip3 install --upgrade tidalapi
```

After upgrading tidalapi, it will often be necessary to delete the existing json file and restart mopidy.
The path will vary, depending on your install method.
```
rm /var/lib/mopidy/tidal/tidal-oauth.json
```
### GStreamer
When using High and Low quality, be sure to install gstreamer bad-plugins, eg. ::
```
sudo apt-get install gstreamer1.0-plugins-bad
```
This is mandatory to be able to play m4a streams.

### Python

Mopidy-Tidal requires python >= 3.7.  3.7 is supported in theory as many people
are still using it on embedded devices, but our test suite does not currently
have 100% coverage under 3.7 (PRs to fix this are welcome!).  Mopidy-Tidal is
fully tested on python >= 3.8.

## Configuration

Before starting Mopidy, you must add configuration for
Mopidy-Tidal to your Mopidy configuration file, if it is not already present.

The configuration is usually stored in `/etc/mopidy/mopidy.conf` or possibly `~/.config/mopidy/mopidy.conf`, depending on your system configuration ::
```
[tidal]
enabled = true
quality = LOSSLESS
#client_id =
#client_secret =
```

Quality can be set to LOSSLESS, HIGH or LOW. Hi_RES(master) is currently not supported.
Lossless quality (FLAC) requires Tidal HiFi Subscription.

Optional: Tidal API `client_id`, `client_secret` can be overridden by the user if necessary.

## OAuth Flow

Using the new OAuth flow, you have to visit a link to connect the mopidy app to your login.

1. When you restart the Mopidy server, check the latest systemd logs and find a line like:
```
journalctl -u mopidy | tail -10
...
Visit link.tidal.com/AAAAA to log in, the code will expire in 300 seconds.
```
2. Go to that link in your browser, approve it, and that should be it.

##### Note: Login process is a **blocking** action, so Mopidy will not load until you approve the application.
The OAuth session will be reloaded automatically when Mopidy is restarted. It will be necessary to perform these steps again if/when the session expires or if the json file is moved.

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
