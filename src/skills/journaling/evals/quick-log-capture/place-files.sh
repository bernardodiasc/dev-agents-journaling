#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
mv env.fixture .env
