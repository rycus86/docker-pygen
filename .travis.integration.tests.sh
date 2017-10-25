#!/usr/bin/env bash

DIND_VERSION=$1

set -e

# install dependencies
pip install -r test-requirements.txt

# run the integration tests
DIND_VERSIONS=${DIND_VERSION} PYTHONPATH=tests python -m unittest -v integrationtest_helper