# https://setuptools.readthedocs.io/en/latest/setuptools.html#test-build-package-and-run-a-unittest-suite
import os
import json
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

# http://www.digip.org/blog/2011/01/generating-data-files-in-setup.py.html
setup(
        name                = 'booque',
        version             = '0.0.1',
        author              = 'Martijn van Beers',
        author_email        = 'martijn@idfuse.nl',
        description         = 'scopus-like boolean query parser/translator',
        packages            = find_packages(),
        url                 = 'https://github.com/martijnvanbeers/booque',
        install_requires    = [ 'pyparsing', 'click' ],

# https://docs.pytest.org/en/latest/goodpractices.html#integrating-with-setuptools-python-setup-py-test-pytest-runner
        setup_requires      = [ 'pytest-runner' ],
        tests_require       = [ 'pytest' ],
        entry_points        = {
            'console_scripts': [
                'booque_parse = booque.commands.parse_input:run',
            ],
        },
    )
