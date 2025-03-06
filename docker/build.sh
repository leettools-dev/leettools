#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/.. && pwd)"

org_name="leettools"
app_name="leettools"
# read the version number project.toml file and use in the docker image
version=$(grep "^version = " "$BASE_DIR"/pyproject.toml | cut -d'"' -f2)

# check if the version number is valid
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid version number: $version"
    exit 1
fi

echo "Building docker image with version: $version"

pushd . > /dev/null

cd "$BASE_DIR"

cp "$DIR"/dockerignore.template "$BASE_DIR"/.dockerignore
cat "$BASE_DIR"/.gitignore >> "$BASE_DIR"/.dockerignore

docker build -t "${org_name}/${app_name}":"${version}" -f "$DIR"/Dockerfile "$BASE_DIR"

# tag the image with the latest version
docker tag "${org_name}/${app_name}":"${version}" "${org_name}/${app_name}":latest

popd > /dev/null
