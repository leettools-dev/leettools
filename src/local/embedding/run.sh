#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/../../.. && pwd)"

# echo "Running local embedding service, the BASE_DIR is $BASE_DIR"

if [ ! -f "$BASE_DIR/.env" ]; then
    echo "Please create a .env file in the project root ${BASE_DIR}"
    exit 1
fi

while IFS='=' read -r name value; do
    if [[ ! $name =~ ^\# ]] && [[ -n $name ]]; then
        export "$name=$value";
    fi;
done < "$BASE_DIR/.env"

if [ -z "${LEET_HOME-}" ]; then
    DEFAULT_LOG_ROOT="/tmp/leettools/logs/svc"
else
    DEFAULT_LOG_ROOT="${LEET_HOME}/logs/svc"
fi

LOG_OUTPUT=${LOG_OUTPUT:-"console"}
EDS_LOG_ROOT=${EDS_LOG_ROOT:-"${DEFAULT_LOG_ROOT}"}
logSizeLimit=${LOG_SIZE_LIMIT:-"10M"}
logFileSig=${LOG_FILE_SIG:-"svc"}-embedding
logDir=${EDS_LOG_ROOT}/${logFileSig}
mkdir -p "$logDir"

# re-export so that logPostProcess can use it
export LOG_FILE_SIG=$logFileSig
export LOG_SIZE_LIMIT=$logSizeLimit
export LOG_DIR=$logDir

set +e
which rotatelogs >/dev/null 2>&1
hasRotateLogs=$?
if [ "$hasRotateLogs" == "1" ]; then
    echo "No rotatelogs installed on system. Please install the httpd package."
    exit 1;
fi
set -e

cd "$BASE_DIR"

if [[ "$LOG_OUTPUT" == "console" ]]; then
    python src/local/embedding/local_embdedding_service.py \
            --host "${EDS_DEFAULT_EMBEDDING_SERVICE_HOST:-0.0.0.0}" \
            --port "${EDS_DEFAULT_EMBEDDING_SERVICE_PORT:-8001}" \
            --log-level "${EDS_LOG_LEVEL:-INFO}"
else
    python src/local/embedding/local_embdedding_service.py \
        --host "${EDS_DEFAULT_EMBEDDING_SERVICE_HOST:-0.0.0.0}" \
        --port "${EDS_DEFAULT_EMBEDDING_SERVICE_PORT:-8001}" \
        --log-level "${EDS_LOG_LEVEL:-INFO}" 2>&1 \
        | rotatelogs -L "${logDir}"/latest.log -f -c \
        -p "$BASE_DIR"/scripts/log_postprocess.sh "${logDir}"/"${logFileSig}".%Y-%m-%d-%H-%M.log "$logSizeLimit"
fi
