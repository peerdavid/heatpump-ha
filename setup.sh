#!/bin/bash


pip3 install -r requirements.txt

cd ..
git pull pip3 install https://github.com/peerdavid/htheatpump
cd htheatpump
pip install -e .