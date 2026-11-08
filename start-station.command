#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -x /opt/homebrew/bin/python3 ]; then
 SIGNAL_PYTHON=/opt/homebrew/bin/python3
else
 SIGNAL_PYTHON=python3
fi
exec "$SIGNAL_PYTHON" -m station.server --port 18765 --db ../../work/station-data.nosync/station.sqlite3 "$@"
