#!/bin/bash
sudo apt-get update && sudo apt-get upgrade
&& dpkg --set-selections < packages.txt
&& sudo apt-get dselect-upgrade
&& python3 -m venv ./venv
&& source ./venv/bin/activate
&& pip install -r requirements.txt
deactivate
