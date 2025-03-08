#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/.. && pwd)"

# check if the .env file exists in the base directory
if [ ! -f "$BASE_DIR/.env" ]; then
    echo ".env file not found in $BASE_DIR. Using all default values."
    echo "" >> "$BASE_DIR/.env"
fi

pushd . > /dev/null

cd "$DIR"
# shellcheck disable=SC1091
source docker_util.sh

# check if the docker image exists
# read the images from the docker-compose.yml file
# replace ${LEETTOOLS_VERSION} and ${LEETTOOLS_WEB_VERSION} with the actual env vars
images=$(grep 'image:' docker-compose.yml | sed 's/image: //')

# check if the docker image exists
for image in $images; do
    # replace ${LEETTOOLS_VERSION} and ${LEETTOOLS_DEV_VERSION} with the actual env vars
    # shellcheck disable=SC2001
    image=$(echo "$image" | sed "s/\${LEETTOOLS_VERSION}/${LEETTOOLS_VERSION}/")
    # shellcheck disable=SC2001
    image=$(echo "$image" | sed "s/\${LEETTOOLS_WEB_VERSION}/${LEETTOOLS_WEB_VERSION}/")  
    # Split image name and tag
    image_name=$(echo "$image" | cut -d: -f1)
    image_tag=$(echo "$image" | cut -d: -f2)
    if ! docker images "$image_name" | grep -q "$image_tag"; then
        echo "Docker image $image does not exist. Pulling the image..."
        docker pull "$image"
    fi
done

docker compose down || true
docker compose up -d

popd > /dev/null

echo "LeetTools Docker containers started."