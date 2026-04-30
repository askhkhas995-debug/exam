#!/bin/sh
set -eu
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
pforge validate || true
