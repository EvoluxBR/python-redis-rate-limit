#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('requirements.txt') as f:
    requires = f.readlines()

setup(
    name='python-redis-rate-limit',
    version='0.0.4',
    description=u'Python Rate Limiter based on Redis.',
    long_description=readme,
    author=u'Victor Torres',
    author_email=u'vpaivatorres@gmail.com',
    url=u'https://github.com/evoluxbr/python-redis-rate-limit',
    license=u'MIT',
    packages=find_packages(exclude=('tests', 'docs')),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License'
    ],
    install_requires=requires
)
