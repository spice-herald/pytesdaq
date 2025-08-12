import os
import glob
import shutil
from setuptools import setup, find_packages, Command
import codecs
from os import path


# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
      long_description = f.read()


# set up automated versioning reading    
def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

setup(name='pytesdaq',
      version=get_version('pytesdaq/_version.py'),
      description='DAQ and Intruments control for TES development',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Bruno Serfass',
      author_email='serfass@berkeley.edu',
      url="https://github.com/spice-herald/pytesdaq",
      zip_safe = False,
      include_package_data = True,
      package_data = {
          '': ['*.ini'],
      },
      packages = find_packages(),
      install_requires=[
            'PyQt5',
            'matplotlib',
            'lakeshore',
            'pandas',
            'nidaqmx',
            'pyvisa',
            'paramiko>=3.2.0',
            'walrus',
            'h5py',
            'qetpy>=1.8.0',
            'scipy',
            'seaborn',
            'astropy',
            'lmfit',
            'tables'
      ],
)
