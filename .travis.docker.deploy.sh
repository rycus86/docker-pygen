#!/usr/bin/env bash

if [ "${TRAVIS_BRANCH}" != "master" ]; then
  echo 'Not pushing to Docker Hub'
  exit 0
fi

docker login -u="rycus86" -p="${DOCKER_PASSWORD}"

for DOCKER_TAG in $@; do
  docker push rycus86/docker-pygen:${DOCKER_TAG}
done
