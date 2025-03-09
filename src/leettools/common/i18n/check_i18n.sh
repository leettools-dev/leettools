#!/bin/bash

# shellcheck disable=SC2045
for lang_dir in $(ls -d locales/*/); do
    lang=$(sed 's|^locales/||;s|/||' <<< "$lang_dir")
    if [ "$lang" == "en" ]; then
        continue
    fi
    message_file=$lang_dir/LC_MESSAGES/messages.po
    if [ ! -f "$message_file" ]; then
        echo "No message file found for $lang"
        continue
    fi
    empty_msgstr=$(grep -E 'msgstr ""|msgstr ""' "$message_file")
    # remove the first line of the results
    empty_msgstr=$(sed '1d' <<< "$empty_msgstr")
    if [ -n "$empty_msgstr" ]; then
        echo "Empty msgstr found for $lang:"
        location_str=$(grep -B 3 -E 'msgstr ""|msgstr ""' "$message_file")
        # remove the first 5 lines of the results
        location_str=$(sed '1,5d' <<< "$location_str")
        echo "$location_str"
    fi
done