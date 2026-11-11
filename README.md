# Authors’ Contributions

A local desktop tool for preparing CRediT author contribution statements.

## Quick start

Requires Python 3.10 or later with Tkinter.

    python -m pip install -r requirements.txt
    python author_contributions.py

On Windows, you can also run run_server.bat after installing dependencies.
On Linux, install your distribution's Tkinter package if necessary (often python3-tk).

## Features

- English by default; switch to Chinese using Language. The choice is remembered.
- Enter English names, Chinese names, or both. Single names are supported.
- Chinese names convert to pinyin: 张绪霞 → Zhang Xuxia.
- Assign the 14 CRediT roles, reorder authors, and generate statements.
- Save/load JSON projects, copy statements, and export plain text.
- Create custom templates using {authors} and {role}.

## Workflow

1. Add authors. An optional ID distinguishes people with the same name.
2. Click table cells to assign contributions.
3. Choose a template and click Generate.
4. Review the statement, then copy or export it.

Regenerate after changing names, roles, ordering, or templates.
Templates named after publishers are examples, not official submission rules.
Pinyin, surname boundaries, polyphonic characters, and initials require human review.
TXT export produces plain text, not a Word document.

## Local data

The app runs locally. settings.json stores the language preference;
custom_formats.json stores templates beside the script. Saved author projects may
contain personal information. These default local files are ignored by Git.
Use the sanitized example in examples/ to try loading a project.

## Development

    python -m unittest discover -s tests -v

See CONTRIBUTING.md and RELEASE_CHECKLIST.md.

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 MaQ.

中文说明见 README.zh-CN.md。

## Team favorites
Save entered names or current authors to Team favorites. Double-click a favorite to add it to the current project. Favorites persist in common_names.json; each new session starts with empty authors and assignments. This personal roster is excluded from Git.
