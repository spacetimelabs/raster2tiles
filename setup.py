# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


setup(name='raster2tiles',
      version='0.0.3',
      packages=find_packages(),
      python_requires='>=2.7,<3',
      setup_requires=['Cython>=0.25.2', 'numpy>=1.13.1'],
      install_requires=[
        'backports.shutil-get-terminal-size>=1.0.0',
        'cycler>=0.10.0',
        'decorator>=4.1.2',
        'enum34>=1.1.6',
        'functools32>=3.2.3.post2',
        'GDAL==2.2.1',
        'numpy>=1.13.1',
        'olefile>=0.44',
        'pathlib2>=2.3.0',
        'pexpect>=4.2.1',
        'pickleshare>=0.7.4',
        'Pillow>=4.2.1',
        'prompt-toolkit>=1.0.15',
        'psycopg2>=2.7.3.1',
        'ptyprocess>=0.5.2',
        'Pygments>=2.2.0',
        'pyparsing>=2.2.0',
        'python-dateutil>=2.6.1',
        'pytz>=2017.2',
        'scandir>=1.5',
        'scipy>=0.19.1',
        'simplegeneric>=0.8.1',
        'six>=1.10.0',
        'SQLAlchemy>=1.2.0b2',
        'subprocess32>=3.2.7',
        'traitlets>=4.3.2',
        'wcwidth>=0.1.7'
      ],
      entry_points='''
        [console_scripts]
        raster2tiles=raster2tiles.cli:go
      ''',
      zip_safe=False,
      author='Spacetime Labs',
      author_email='dev@spacetimelabs.ai',
)
