#!/bin/bash
# Use yum instead of apt-get:
sudo yum install python3-pip

# Install virtualenv
sudo pip3 install virtualenv
virtualenv -p python3 venv
source venv/bin/activate

# Install dependecies
pip3 install -r requirement.txt