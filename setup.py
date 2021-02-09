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
      install_requires = ['pyramid', 'pyramid_mako', 'pyramid_exclog', 'pyramid_debugtoolbar', 'configparser', 'waitress', 'pdoc3', 'mkdocs', 'mysql-connector-python'],
      entry_points = {
        'paste.app_factory': [
            'main = pytesdaq.display:main',
        ],
      },
  )
