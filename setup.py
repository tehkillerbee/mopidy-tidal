from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-Tidal',
    version=get_version('mopidy_tidal/__init__.py'),
    url='https://github.com/mones88/mopidy-tidal',
    license='Apache License, Version 2.0',
    author='Simone Fantini',
    author_email='mones88@gmail.com',
    description='Tidal music service integration',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    dependency_links=[
        'git+https://github.com/quodrum-glas/python-tidal.git#egg=python-tidal-0.6.7',
    ],
    install_requires=[
        'setuptools',
        'Mopidy >= 1.0',
        'Pykka >= 1.1',
        'tidalapi == 0.6.7',
        'requests >= 2.0.0',
        'mutagen >= 1.36',
    ],
    entry_points={
        'mopidy.ext': [
            'tidal = mopidy_tidal:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
