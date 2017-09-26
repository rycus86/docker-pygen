#!/usr/bin/env bash

set -e
set -x

docker login -u="rycus86" -p="${DOCKER_PASSWORD}"

for DOCKER_TAG in $@; do
  docker push rycus86/docker-pygen:${DOCKER_TAG}
done
