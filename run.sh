#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
python -m streamlit run app.py "$@"
