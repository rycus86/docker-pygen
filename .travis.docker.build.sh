#!/usr/bin/env bash

DOCKERFILE=$1
DOCKER_TAG=$2
WORKER_DOCKER_TAG=$3

echo 'Enable other architectures ...'
docker run --rm --privileged multiarch/qemu-user-static:register --reset

echo 'Building the main image...'

docker build -t docker-pygen:${DOCKER_TAG} -f ${DOCKERFILE} .
docker tag docker-pygen:${DOCKER_TAG} rycus86/docker-pygen:${DOCKER_TAG}

echo 'Setting up the Swarm worker image...'

echo "FROM rycus86/docker-pygen:${DOCKER_TAG}" > Dockerfile.tmp
echo 'ENTRYPOINT [ "python", "swarm_worker.py" ]' >> Dockerfile.tmp

echo "Building the Swarm worker image with $WORKER_DOCKER_TAG tag..."

docker build -t docker-pygen:${WORKER_DOCKER_TAG} -f Dockerfile.tmp .
docker tag docker-pygen:${WORKER_DOCKER_TAG} rycus86/docker-pygen:${WORKER_DOCKER_TAG}
