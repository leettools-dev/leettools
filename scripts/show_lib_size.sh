#!/bin/bash

pip list --format=freeze | cut -d= -f1 | while read package; do
    location=$(pip show "$package" | grep 'Location:' | cut -d' ' -f2)
    package_path="$location/$package"
    if [ -d "$package_path" ]; then
        du -sh "$package_path"
    else
        echo "N/A:    $package_path [$package]"
    fi
done
