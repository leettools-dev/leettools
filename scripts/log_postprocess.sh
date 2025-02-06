#!/usr/bin/env bash

set -u -e

logFileLimit=${LOG_FILE_LIMIT:-50};
logFileSig=${LOG_FILE_SIG};
logDir=${LOG_DIR}

echo "logFileLimit is $logFileLimit, logFileSig is $logFileSig, logDir is $logDir";

logFileCount=$(find "$logDir" -name "${logFileSig}*.log" | wc -l)

extraCount=$((logFileCount-logFileLimit))

if [[ $extraCount  -gt 0 ]]; then
    find "$logDir" -name "${logFileSig}*.log" -type f -printf '%T@ %p\n' | sort -n | head -n $extraCount | cut -d' ' -f2- | while read -r x; do
        echo "Removing $x due to log number has reached $logFileLimit";
        rm "$x"
    done
else
    echo "File count $logFileCount has not reached file limit $logFileLimit yet. No need to prune."
fi
