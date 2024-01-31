#!/usr/bin/bash

check_command_success() {
    echo "$@"
    "$@"
    if [ $? -eq 0 ]; then
        echo "Command successful"
    else
        echo "Command failed"
        exit 1
    fi
}


echo $PWD

mkdir code
cd code

# create tarbal
check_command_success CMD_COPY

echo $PWD

cd "$(dirname "$0")"

echo $PWD

ls -la
#pwd

PREVIOUSCOMMANDS

SETUPCOMMAND

# command to execute
check_command_success CMD

# delete files that where copied from the code directory
DELETEFILES