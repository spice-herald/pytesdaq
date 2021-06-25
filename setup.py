from setuptools import setup, find_packages

setup(name='pytesdaq',
      version='0.1.0',
      description='DAQ and Intruments control for TES development',
      author='Bruno Serfass',
      author_email='serfass@berkeley.edu',
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
          'paramiko',
          'walrus',
          'h5py',
          'qetpy',
          'scipy',
          'seaborn',
          'astropy',
      ],
)
