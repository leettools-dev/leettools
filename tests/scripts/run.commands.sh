#!/bin/bash

# Test program for CLI commands
#
# To run the command, in the root directory of the project, run the following command:
# 
# bash tests/scripts/run.commands.sh
#
# This script will create a new KB, ask a question, and then remove the KB.

run_command() {
  local ts="$1"
  local cmd="$2"
  local logfile="command_output.${ts}.log"

  echo "Testing command: $cmd, output saved to $logfile"

  # Execute the command, saving both stdout and stderr to the logfile
  eval "$cmd" >"$logfile" 2>&1
  local exit_status=$?

  # If the command failed (non-zero exit status), print an error message
  if [ $exit_status -ne 0 ]; then
    echo "Error: Command '$cmd' failed with exit status $exit_status. See '$logfile' for details."
  else
    echo "Command succeeded."
  fi

  return $exit_status
}

# create a timestamp in the format of "yyyymmdd_HHMMSS"
ts=$(date "+%Y%m%d_%H%M%S")
kb="test_kb_${ts}"

run_command "$ts" "leet kb create -k $kb -l DEBUG"

run_command "$ts" "leet flow -t answer -k $kb -q 'How does GraphRag work' -l DEBUG"

run_command "$ts" "leet kb remove -k $kb"

