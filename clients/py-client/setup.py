#!/usr/bin/env python
from setuptools import find_packages
from setuptools import setup
import datetime

CURRENT_VERSION = "1.1.0"

# ### PYPI VERSION. ###
date_tmpl = '{dt:%y}.{dt.month}.{dt.day}.{dt.hour}.{dt.minute}.{dt.second}'
VERSION = ".".join([CURRENT_VERSION, date_tmpl.format(dt=datetime.datetime.now())])
#######################

# Packages used
regular_packages = [
    'pandas',
    'requests'
]

# This is where the magic happens
setup(name='groundhog',
      version=VERSION,
      description='groundhog API client',
      author='Brad Beechler, James Lamb',
      author_email='brad.beechler@uptake.com, jaylamb20@gmail.com',
      packages=find_packages(),
      install_requires=[regular_packages],
      include_package_data=True,
      extras_require={
          'all': regular_packages
      },
      zip_safe=False,
      test_suite="tests"
      )
