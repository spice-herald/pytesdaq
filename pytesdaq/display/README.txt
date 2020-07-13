website for pytesdaq
============

Getting Started
---------------

- Go to main directory

    cd pytesdaq

- Create a Python virtual environment.

    python3 -m venv env

- Upgrade packaging tools.

    env/bin/pip install --upgrade pip setuptools

- Install the project in editable mode with its testing requirements.

    env/bin/pip install -e ".[testing]"

- Run your project's tests

    env/bin/pytest

- Run your project. – This will run the project on localhost.

    env/bin/pserve pytesdaq/display/development.ini
