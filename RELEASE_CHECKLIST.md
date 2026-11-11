# Release checklist

- [x] MIT license added; copyright attribution: 2026 MaQ.
- [ ] Run the tests and manually check both interface languages.
- [ ] Review pinyin, author ordering, template previews, project loading, and TXT output.
- [ ] Review git status and the staged diff; exclude personal projects, .venv, settings, and custom templates.
- [ ] Create an empty GitHub repository, then upload the source and documentation.
- [ ] Confirm GitHub Actions passes before tagging a release.

Suggested repository name: authors-contributions
Suggested description: A bilingual desktop CRediT author contribution statement generator.

Git commands, after creating an empty repository:
    git init
    git add .
    git status
    git diff --cached
    git commit -m "Initial public release"
    git branch -M main
    git remote add origin YOUR_REPOSITORY_URL
    git push -u origin main

Known limitations: pinyin and initials require review; publisher templates are examples;
some detailed error messages remain Chinese; export is TXT only.
