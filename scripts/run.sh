#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/.. && pwd)"

# read the optional .env filename if specified on command line using -e flag
# default is .env
ENV_FILE=".env"

while getopts ":e:" opt; do
  case ${opt} in
    e )
      ENV_FILE=$OPTARG
      # if the file does not exist, exit
      if [ ! -f "${BASE_DIR}"/"${ENV_FILE}" ]; then
        echo "Specified env file not found: ${BASE_DIR}/${ENV_FILE}"
        exit 1
      fi
      ;;
    \? )
      echo "Usage: $0 [-e] <env_file>"
      exit 1
      ;;
  esac
done 


# Check if the .env file exists in the root directory
if [ -f "${BASE_DIR}"/"${ENV_FILE}" ]; then
  #Load environment variables from .env file
    while IFS='=' read -r name value; do 
    if [[ ! $name =~ ^\# ]] && [[ -n $name ]]; then
      # echo "$name" "$value";
      export "$name=$value"; 
    fi; 
    done < "${BASE_DIR}"/"${ENV_FILE}"
fi

# if LEET_HOME is set, we will have a default value for EDS_LOG_ROOT
if [ -z "${LEET_HOME-}" ]; then
    DEFAULT_LOG_ROOT="/tmp/leettools/logs/svc"
else
    DEFAULT_LOG_ROOT="${LEET_HOME}/logs/svc"
fi

LOG_OUTPUT=${LOG_OUTPUT:-"console"}
EDS_LOG_ROOT=${EDS_LOG_ROOT:-"${DEFAULT_LOG_ROOT}"}
logSizeLimit=${LOG_SIZE_LIMIT:-"10M"}
logFileSig=${LOG_FILE_SIG:-"svc"}-eds
logDir=${EDS_LOG_ROOT}/${logFileSig}
mkdir -p "$logDir"

if [ -n "${GIT_SHA-}" ]; then
    echo "${GIT_SHA}" > "$logDir"/git_sha.txt
else
    echo "NOT SPECIFIED" > "$logDir"/git_sha.txt
fi

# re-export so that logPostProcess can use it
export LOG_FILE_SIG=$logFileSig
export LOG_SIZE_LIMIT=$logSizeLimit
export LOG_DIR=$logDir

set +e
if [ "$LOG_OUTPUT" == "FILE" ]; then
    which rotatelogs >/dev/null 2>&1
    hasRotateLogs=$?
    if [ "$hasRotateLogs" == "1" ]; then
        echo "No rotatelogs installed on system. Please install the httpd package."
        exit 1;
    fi
fi
set -e

cd "$BASE_DIR"

chmod +x "$BASE_DIR"/scripts/log_postprocess.sh

if [[ "$LOG_OUTPUT" = "console" ]]; then
    python -m leettools.svc.main  \
            --host "${API_SERVICE_HOST:-0.0.0.0}" \
            --port "${API_SERVICE_PORT:-8000}" \
            --log-level "${EDS_LOG_LEVEL:-INFO}"
else
    python -m leettools.svc.main  \
        --host "${API_SERVICE_HOST:-0.0.0.0}" \
        --port "${API_SERVICE_PORT:-8000}" \
        --log-level "${EDS_LOG_LEVEL:-INFO}" 2>&1 \
        | rotatelogs -L "${logDir}"/latest.log -f -c \
        -p "$BASE_DIR"/scripts/log_postprocess.sh "${logDir}"/"${logFileSig}".%Y-%m-%d-%H-%M.log "$logSizeLimit"
fi
