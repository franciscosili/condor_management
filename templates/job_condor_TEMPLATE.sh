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
ls -la

check_command_success mkdir code
check_command_success cd code

# create tarbal
COPYCOMMAND

echo $PWD

ls -la
#pwd

PREVIOUSCOMMANDS

SETUPCOMMAND

# command to execute
check_command_success CMD

# delete files that where copied from the code directory
DELETEFILES