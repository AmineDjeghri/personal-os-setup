#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-personal-os-setup-arch-test}"

cd "$(dirname "$0")/../.." # repo root (personal-os-setup/)

docker build -f tests/archlinux/Dockerfile -t "$IMAGE_NAME" .
docker run --rm -it -v "$(pwd):/home/tester/personal-os-setup" "$IMAGE_NAME"
