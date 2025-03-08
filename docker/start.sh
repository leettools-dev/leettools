#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# check if the .env file exists in the docker directory
env_file="$DIR/.env"
template_file="$DIR/env.template"
if [ ! -f "$env_file" ]; then
    # copy the .env.template file to .env if it doesn't exist
    cp "$template_file" "$env_file"
    echo ".env file not found in $DIR for docker-compose.yml. Copied from $template_file."
fi

# load the .env file into the environment by exporting the variables
while IFS='=' read -r name value; do
if [[ ! $name =~ ^\# ]] && [[ -n $name ]]; then
    # we only export the variables that are not set in the environment
    current_env_value="${!name:-}"
    if [ -z "${current_env_value}" ]; then
        export "$name=$value";
    else
        # print a warning message if the two values are different
        if [ "${current_env_value}" != "${value}" ]; then
            echo "[start.sh warning] $name is set to $current_env_value in the current environment, but the $env_file file has a different value: $value"
        fi;
    fi;
fi;
done < "${env_file}"

if [ -z "${LEET_HOME:-}" ]; then
    case "$(uname -s)" in
        Darwin|Linux)
            LEET_HOME=~/leettools
            ;;
        CYGWIN*|MINGW*|MSYS*)
            LEET_HOME="$USERPROFILE/leettools"
            ;;
        *)
            echo "Unsupported operating system, using the value from .env file"
            ;;
    esac
    echo "LEET_HOME is not set, using the default value: $LEET_HOME"
    export LEET_HOME="$LEET_HOME"
fi

# set DOCUMENETS_HOME to the Documents directory on different OS
# windows: C:\Users\<username>\Documents
# mac: ~/Documents
# linux: ~/Documents

# if no DOCUMENETS_HOME is set in the .env file, set it to the Documents directory on different OS
if [ -z "${DOCUMENETS_HOME:-}" ]; then
    case "$(uname -s)" in
        Darwin|Linux)
            export DOCUMENETS_HOME=~/Documents
            ;;
        CYGWIN*|MINGW*|MSYS*)
            export DOCUMENETS_HOME="$USERPROFILE/Documents"
            ;;
        *)
            echo "Unsupported operating system, using the value from .env file"
            ;;
    esac
fi

pushd . > /dev/null

cd "$DIR"

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