#!/usr/bin/env bash

python -m nuitka \
  --standalone \
  --enable-plugin=pyside6 \
  --include-package=numpy \
  --output-dir=build \
  --output-filename=switchblade \
  src/main.py
