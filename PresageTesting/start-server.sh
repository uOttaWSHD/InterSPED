#!/bin/bash
# Start script for Presage Hello Vitals

cd /app

# If no arguments, run hello_vitals interactively
if [ $# -eq 0 ]; then
    exec ./build/hello_vitals
else
    # Pass arguments to hello_vitals
    exec ./build/hello_vitals "$@"
fi
