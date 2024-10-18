#!/bin/bash
sudo apt-get update &&
sudo apt-get upgrade -y &&
while read -r p; do sudo apt-get install -y "$p"; done < packages.txt &&
python3 -m venv ./venv &&
./venv/bin/pip install -r requirements.txt
