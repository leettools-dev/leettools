#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

pushd . > /dev/null

cd "$DIR"
# shellcheck disable=SC1091
source docker_util.sh

docker compose --profile full down

popd > /dev/null

echo "LeetTools Docker containers stopped."

