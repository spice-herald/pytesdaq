Website for pytesdaq data storage
===================================

Getting Started – Installation of tools and packages for Pyramid
-----------------------------------------------------------------

**Let the pytesdaq git directory root be `~/`.**

- Go to display directory.

    `cd ~/pytesdaq/display/`

- Create a Python virtual environment.

    `python3 -m venv env`

- Upgrade packaging tools.

    `env/bin/pip install --upgrade pip setuptools`

- Install the project in editable mode with its testing requirements.

    `cd ~/`

    `pytesdaq/display/env/bin/pip install -e ".[testing]"`

- Run the project on localhost.

    `cd ~/pytesdaq/display/`

    `env/bin/pserve development.ini`


IN ONE COMMAND, FROM pytesdaq directory:
`pip install . --user; cd pytesdaq/display/; python3 -m venv env; env/bin/pip install --upgrade pip setuptools; cd ../..; pytesdaq/display/env/bin/pip install -e ".[testing]"; cd pytesdaq/display/; env/bin/pserve development.ini`

Database Access
-----------------

Database controls are in `~/pytesdaq/display/db.py`. The current database settings are:

host="192.168.1.177", port=3306, user="daqtest", password="password123", for mysql on Remi Seddigh's machine.
