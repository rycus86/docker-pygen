#!/usr/bin/env bash

DOCKER_TAG=${ARCH}
WORKER_DOCKER_TAG="worker-$ARCH"
BASE_IMAGE=${BASE_IMAGE:-alpine}
GIT_COMMIT=${TRAVIS_COMMIT}
BUILD_TIMESTAMP=$(date +%s)

set -e

echo 'Enable other architectures ...'
docker run --rm --privileged multiarch/qemu-user-static:register --reset

echo 'Building the main image...'

docker build -t docker-pygen:${DOCKER_TAG}               \
        --build-arg BASE_IMAGE=${BASE_IMAGE}             \
        --build-arg GIT_COMMIT=${GIT_COMMIT}             \
        --build-arg BUILD_TIMESTAMP=${BUILD_TIMESTAMP}   \
        .

docker tag docker-pygen:${DOCKER_TAG} rycus86/docker-pygen:${DOCKER_TAG}

echo 'Setting up the Swarm worker image...'

echo "FROM rycus86/docker-pygen:${DOCKER_TAG}" > Dockerfile.tmp
echo 'ENTRYPOINT [ "python", "swarm_worker.py" ]' >> Dockerfile.tmp

echo "Building the Swarm worker image with $WORKER_DOCKER_TAG tag..."

docker build -t docker-pygen:${WORKER_DOCKER_TAG}        \
        --build-arg GIT_COMMIT=${GIT_COMMIT}             \
        --build-arg BUILD_TIMESTAMP=${BUILD_TIMESTAMP}   \
        -f Dockerfile.tmp .

docker tag docker-pygen:${WORKER_DOCKER_TAG} rycus86/docker-pygen:${WORKER_DOCKER_TAG}
