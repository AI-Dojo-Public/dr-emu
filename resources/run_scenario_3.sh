#!/bin/bash

pip install -e cyst-core
pip install -e beast-demo
pip install requests
pip install pyaml

python beast-demo/scenario_3.py
