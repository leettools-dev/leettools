#!/bin/bash

# this program is used to start the docker container for the leettools service

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/.. && pwd)"

# read the optional .env filename if specified on command line using -e flag
# default is .env
ENV_FILE=".env"

# Default values
FORCE_REMOVE=false

# Initialize MOUNT_DIRS as an array
declare -a MOUNT_DIRS=()

while getopts ":e:fm:" opt; do
  case ${opt} in
    e )
      ENV_FILE=$OPTARG
      # if the file does not exist, exit
      if [ ! -f "${BASE_DIR}"/"${ENV_FILE}" ]; then
        echo "Specified env file not found: ${BASE_DIR}/${ENV_FILE}"
        exit 1
      fi
      ;;
    f )
      FORCE_REMOVE=true
      ;;
    m )
      # Split multiple mount directories by comma and add to array
      IFS=',' read -ra MOUNTS <<< "$OPTARG"
      for mount in "${MOUNTS[@]}"; do
        MOUNT_DIRS+=("$mount")
      done
      ;;
    \? )
      echo "Usage: $0 [-e <env_file>] [-f] [-m <mount_dirs>]"
      echo "  -e <env_file>  Specify environment file (default: ${BASE_DIR}/.env)"
      echo "  -f             Force remove existing container"
      echo "  -m <mount_dirs> Specify comma-separated directories to mount (format: src:dest[,src2:dest2,...])"
      exit 1
      ;;
  esac
done

# convert MOUNT_DIRS array to mount options
mount_opts=""
if [ ${#MOUNT_DIRS[@]} -gt 0 ]; then
  for mount in "${MOUNT_DIRS[@]}"; do
    mount_opts+="-v $mount:ro "
  done
fi

org_name="leettools"
app_name="leettools"
container_name="leettools"

# If force remove is enabled, stop and remove existing container
if [ "$FORCE_REMOVE" = true ]; then
  # Check if container exists and is running
  if docker ps | grep -q "$container_name"; then
    echo "Stopping running $container_name container..."
    docker stop "$container_name" 2>/dev/null || true
  fi
  # Check if container exists (running or not)
  if docker ps -a | grep -q "$container_name"; then
    echo "Removing $container_name container..."
    docker rm "$container_name" 2>/dev/null || true
  fi
else
  # Check if container exists (running or not)
  if docker ps -a | grep -q "$container_name"; then
    echo -e "\033[1;33mWarning:\033[0m  $container_name container already exists" >&2
    echo -e "\033[1;33mSolution:\033[0m Use -f flag to force remove existing container" >&2
    exit 1
  fi
fi

# read the version number project.toml file and use in the docker image
version=$(grep "^version = " "$BASE_DIR"/pyproject.toml | cut -d'"' -f2)

# check if the version number is valid
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid version number: $version"
    exit 1
fi

# check if the docker image exists
if ! docker images "${org_name}/${app_name}":"${version}" | grep -q "${version}"; then
    echo "Docker image ${org_name}/${app_name}:${version} does not exist"
    version="latest"
    if ! docker images "${org_name}/${app_name}":"${version}" | grep -q "${version}"; then
        echo "Docker image leettools-dev/leettools:${version} does not exist"
        exit 1
    fi
    echo "Using latest version instead"
fi

# Check if the .env file exists in the root directory
if [ -f "${BASE_DIR}"/"${ENV_FILE}" ]; then
  #Load environment variables from .env file
    while IFS='=' read -r name value; do
    if [[ ! $name =~ ^\# ]] && [[ -n $name ]]; then
      # echo "$name" "$value";
      export "$name=$value";
    fi;
    done < "${BASE_DIR}"/"${ENV_FILE}"
    envfile_opt="--env-file ${BASE_DIR}/${ENV_FILE}"
else
    envfile_opt=""
fi

# check if the LEET_HOME, EDS_DATA_DIR, and EDS_LOG_DIR environment variables are set
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

if [ -z "${EDS_DATA_DIR:-}" ]; then
    EDS_DATA_DIR="${LEET_HOME}/data"
fi

if [ -z "${EDS_LOG_DIR:-}" ]; then
    EDS_LOG_DIR="${LEET_HOME}/logs"
fi

if [ -z "${EDS_API_SERVICE_PORT:-}" ]; then
    EDS_API_SERVICE_PORT=8000
fi

# run the docker container as a service with port 8000:8000
# mount the data directory at $LEET_HOME, $EDS_DATA_DIR, $EDS_LOG_DIR
# run the docker container with the .env.docker file
leet_home_in_docker="/leettools"

# print the docker run command
echo "Running docker container with command:"
echo "docker run -d ${envfile_opt} ${mount_opts} \\
    --name \"$container_name\" \\
    -p \"$EDS_API_SERVICE_PORT\":\"$EDS_API_SERVICE_PORT\" \\
    -e LEET_HOME=\"$leet_home_in_docker\" \\
    -v \"$LEET_HOME\":\"$leet_home_in_docker\" \\
    -v \"$EDS_DATA_DIR\":\"$leet_home_in_docker/data\" \\
    -v \"$EDS_LOG_DIR\":\"$leet_home_in_docker/logs\" \\
    ${org_name}/${app_name}:\"${version}\""

# run the docker container
# shellcheck disable=SC2086
docker run -d ${envfile_opt} ${mount_opts} \
    --name "$container_name" \
    -p "$EDS_API_SERVICE_PORT":"$EDS_API_SERVICE_PORT" \
    -e LEET_HOME="$leet_home_in_docker" \
    -v "$LEET_HOME":"$leet_home_in_docker" \
    -v "$EDS_DATA_DIR":"$leet_home_in_docker/data" \
    -v "$EDS_LOG_DIR":"$leet_home_in_docker/logs" \
    ${org_name}/${app_name}:"${version}"