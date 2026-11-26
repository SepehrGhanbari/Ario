#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
BUNDLE="$(cd -- "$HERE/.." && pwd)"
cd "$HERE"
go test -count=1 ./...
go run . verify "$BUNDLE"
