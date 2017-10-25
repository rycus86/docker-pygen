#!/usr/bin/env bash

set -e

if [ "$ARCH" == "amd64" ]; then
    DOCKER_TAGS="worker"
else
    DOCKER_TAGS="${ARCH} worker-$ARCH"
fi

set -x

docker login -u="rycus86" -p="${DOCKER_PASSWORD}"

for DOCKER_TAG in ${DOCKER_TAGS}; do
  docker push rycus86/docker-pygen:${DOCKER_TAG}
done
