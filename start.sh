#!/bin/bash

source venv/bin/activate

LANGO_SERVER_BASE=http://35.3.62.156:8000 python3 object-detection.py &
python3 pi_screen.py

wait

# SERVER_BASE = "http://35.3.62.156:8000"