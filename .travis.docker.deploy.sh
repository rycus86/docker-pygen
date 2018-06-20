#!/usr/bin/env bash

set -e

DOCKER_TAGS="${ARCH} worker-$ARCH"

set -x

echo ${DOCKER_PASSWORD} | docker login --username "rycus86" --password-stdin

for DOCKER_TAG in ${DOCKER_TAGS}; do
  docker push rycus86/docker-pygen:${DOCKER_TAG}
done
