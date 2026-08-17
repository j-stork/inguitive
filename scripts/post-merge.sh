#!/bin/bash
set -e

# Install Python dependencies into the project's local lib directory
pip install -e ".[dev]" --target .pythonlibs/lib/python3.10/site-packages --quiet 2>/dev/null || \
  pip install -r requirements.txt --target .pythonlibs/lib/python3.10/site-packages --quiet
