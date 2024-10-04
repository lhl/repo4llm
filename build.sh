#!/bin/bash

# pip install build twine
python -m build
rm -rf dist/*
twine upload dist/*
