#!/usr/bin/env bash

python -m nuitka \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-icon=/Users/joerg/dev/switchblade/switchblade/src/resources/images/icon.icns \
  --enable-plugin=pyside6 \
  --include-package=numpy \
  --output-dir=build \
  --output-filename=switchblade \
  src/main.py
