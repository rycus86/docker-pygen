#!/usr/bin/env bash

set -e

DOCKER_TAGS="${ARCH} worker-$ARCH"

set -x

docker login -u="rycus86" -p="${DOCKER_PASSWORD}"

for DOCKER_TAG in ${DOCKER_TAGS}; do
  docker push rycus86/docker-pygen:${DOCKER_TAG}
done
