# Process to update the locale files

All process is done in src/leettools/common/i18n folder.

1. First extract all the strings from the codebase.
```bash
pybabel extract -F babel.cfg -o locales/messages.pot ../..
```

2. Then update the locale files with the new strings.
```bash
for lang_dir in $(ls -d locales/*/); do
    lang=$(sed 's|^locales/||;s|/||' <<< $lang_dir)
    echo "Updating $lang in $lang_dir"
    pybabel update -i locales/messages.pot -d locales -l $lang
done
```

3. Go into each language directory and check the updated po files to see if they are
new strings that need to be added to the pot file, identified by `msgstr ""`.

```bash
bash ./check_i18n.sh
```

If all the po files are up to date, you should see no output from the above commands.

4. Compile the po files.
```bash
pybabel compile -d locales
```

5. Run the unit tests to ensure the translations are working.

In the project root, run the following command to run the unit tests.
```bash
pytest -s tests/leettools/common/test_i18n.py
```

Add the updated translation files to git if updated.