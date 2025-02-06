#!/bin/bash

set -e -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$DIR"/.. && pwd)"

LOG_OUTPUT=${LOG_OUTPUT:-"console"}
EDS_LOG_ROOT=${EDS_LOG_ROOT:-"/tmp/leettools/svc/logs"}
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
which rotatelogs >/dev/null 2>&1
hasRotateLogs=$?
if [ "$hasRotateLogs" == "1" ]; then
    echo "No rotatelogs installed on system. Please install the httpd package."
    exit 1;
fi
set -e

cd "$BASE_DIR"

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
