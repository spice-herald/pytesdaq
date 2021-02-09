website for pytesdaq
============

Getting Started
---------------
Let the git directory root be ~/.

- Go to display directory

    cd ~/pytesdaq/pytesdaq/display/

- Create a Python virtual environment.

    python3 -m venv env

- Upgrade packaging tools.

    env/bin/pip install --upgrade pip setuptools

- Install the project in editable mode with its testing requirements.
    
    cd ~/pytesdaq/

    pytesdaq/display/env/bin/pip install -e ".[testing]"

- Run your project's tests
    
    cd ~/pytesdaq/pytesdaq/display/

    env/bin/pytest

- Run your project. – This will run the project on localhost.

    env/bin/pserve development.ini
