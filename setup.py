# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path

__version__ = '0.0.3'

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]

setup(
    name='raster2tiles',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/spacetimelabs/raster2tiles',
    python_requires='>=2.7,<3',
    setup_requires=['Cython>=0.25.2', 'numpy>=1.13.1'],
    install_requires=install_requires,
    entry_points='''
        [console_scripts]
        raster2tiles=raster2tiles.cli:go
    ''',
    keywords='Rasterio',
    zip_safe=False,
    author='Spacetime Labs',
    author_email='dev@spacetimelabs.ai',
)
