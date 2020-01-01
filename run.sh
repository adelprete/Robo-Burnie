#!/bin/sh
echo "using virtual environment: " "/venv"
python3 -m venv "venv"
source venv/bin/activate
pip3 install -r requirements.txt
nohup python3 -m new_migrators.${1}.scripts ${@:2} &