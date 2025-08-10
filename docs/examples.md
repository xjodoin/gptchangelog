---
title: Examples and Recipes | GPTChangelog
description: Practical examples and recipes for using GPTChangelog in real-world workflows including CI/CD, GitHub releases, custom templates, and multi-language changelogs.
keywords:
  - gptchangelog
  - examples
  - recipes
  - ci/cd
  - github releases
  - conventional commits
  - templates
  - release notes
  - python cli
---

# Examples

This page provides practical examples of using GPTChangelog in different scenarios.

## Basic Examples

### Generating a Changelog

The most basic usage is to generate a changelog from your latest tag:

```bash
gptchangelog generate
```

Example output:

```markdown
## [1.2.0] - 2024-10-20

### ✨ Features
- Add support for interactive editing mode
- Implement automatic conventional commit detection

### 🐛 Bug Fixes
- Resolve issue with version detection on Windows
- Fix token counting logic for large repositories

### 🔄 Changes
- Update default model to gpt-4o
- Improve commit message grouping algorithm
```

### Using Interactive Mode

To review and edit the changelog before saving:

```bash
gptchangelog generate --interactive
```

This will show you the generated changelog and prompt you to edit it before saving.

### Generating a Changelog Between Tags

To generate a changelog between two specific tags:

```bash
gptchangelog generate --since v1.0.0 --to v2.0.0
```

### Outputting to a Different File

To save the changelog to a different file:

```bash
gptchangelog generate --output RELEASE_NOTES.md
```

## Real-World Scenarios

### Pre-Release Workflow

Before creating a new release, generate a changelog to review the changes:

```bash
# Generate changelog without saving
gptchangelog generate --dry-run

# If it looks good, create a new tag
git tag -a v1.2.0 -m "Release v1.2.0"

# Generate and save the final changelog
gptchangelog generate
```

### Release Notes for GitHub

Generate release notes for a GitHub release:

```bash
# Get the previous tag
PREV_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^)
CURRENT_TAG=$(git describe --tags --abbrev=0)

# Generate release notes
gptchangelog generate --since $PREV_TAG --to $CURRENT_TAG --output RELEASE_NOTES.md

# Create GitHub release (using gh CLI)
gh release create $CURRENT_TAG --notes-file RELEASE_NOTES.md
```

### Automated Changelog for CI/CD

In a CI/CD pipeline, automatically generate a changelog for each release:

```bash
#!/bin/bash
# This script is part of a CI/CD pipeline

# Set up environment
pip install gptchangelog

# Get the previous tag
PREV_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^)
CURRENT_TAG=$(git describe --tags --abbrev=0)

# Generate changelog
gptchangelog generate --since $PREV_TAG --to $CURRENT_TAG

# Commit and push the updated changelog
git add CHANGELOG.md
git commit -m "Update changelog for $CURRENT_TAG"
git push origin main
```

## Advanced Examples

### Custom Template Example

Create a custom template for your project:

1. Create a directory for templates:
   ```bash
   mkdir -p .gptchangelog/templates
   ```

2. Create a custom changelog template:
   ```bash
   cat > .gptchangelog/templates/changelog_prompt.txt << 'EOF'
   # $project_name Release Notes

   ## Version $next_version ($current_date)

   Changes since previous release:

   $commit_messages

   Instructions:
   1. Format as a detailed release notes document
   2. Group changes into these categories:
      - New Features
      - Improvements
      - Bug Fixes
      - Security Updates
      - Documentation
   3. For each change, provide a clear description of what changed and why it matters
   4. Highlight breaking changes with a "BREAKING" prefix
   5. Use bullet points for each change
   6. Include credit for contributors where applicable
   EOF
   ```

3. Use the custom template:
   ```bash
   gptchangelog generate
   ```

### Integration with Other Tools

#### Combining with Conventional Commits Validation

Use GPTChangelog with commitlint to enforce conventional commits:

```bash
# Install commitlint
npm install -g @commitlint/cli @commitlint/config-conventional

# Set up commitlint
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js

# Add a pre-commit hook (with husky)
npx husky add .husky/commit-msg 'npx --no -- commitlint --edit "$1"'

# Later, generate a changelog from the well-formatted commits
gptchangelog generate
```

#### Generating Release Notes for Different Audiences

You can generate different types of release notes for different audiences:

```bash
# Technical release notes for developers
gptchangelog generate --output DEVELOPER_NOTES.md

# User-friendly release notes
cat > .gptchangelog/templates/user_changelog.txt << 'EOF'
# What's New in $project_name $next_version

Release Date: $current_date

$commit_messages

Instructions:
1. Write this as a user-friendly document explaining what's new
2. Focus on benefits and improvements from the user's perspective
3. Avoid technical details unless they directly affect users
4. Use simple, clear language
5. Group into "New Features", "Improvements", and "Fixed Issues"
EOF

TEMPLATE_PATH=.gptchangelog/templates/user_changelog.txt gptchangelog generate --output WHATS_NEW.md
```

#### Multi-Language Changelogs

Generate changelogs in multiple languages:

```bash
# First, generate the English changelog
gptchangelog generate --output CHANGELOG.en.md

# Then, generate a French version using a translator API or service
cat CHANGELOG.en.md | translator_service en fr > CHANGELOG.fr.md

# Alternatively, use GPT for translation
cat > .gptchangelog/templates/french_changelog.txt << 'EOF'
# Changelog in French

English changelog:
$commit_messages

Instructions:
1. Translate the above changelog to French
2. Maintain the same structure and meaning
3. Use appropriate French terminology for technical terms
EOF

# Then use this template to generate the French changelog
TEMPLATE_PATH=.gptchangelog/templates/french_changelog.txt gptchangelog generate --dry-run > CHANGELOG.fr.md
```

## Examples for Specific Project Types

### Python Package Example

For a Python package:

```bash
# Before a new release
# 1. Update version in setup.py or __init__.py
# 2. Generate changelog
gptchangelog generate
# 3. Commit changes
git add CHANGELOG.md setup.py
git commit -m "Prepare release X.Y.Z"
# 4. Create tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"
# 5. Push changes and tag
git push origin main --tags
# 6. Build and publish
python -m build
twine upload dist/*
```

### JavaScript/Node.js Project Example

For a Node.js project:

```bash
# Before a new release
# 1. Update version in package.json
npm version patch # or minor, or major
# 2. Generate changelog
gptchangelog generate
# 3. Commit changes
git add CHANGELOG.md
git commit -m "Update changelog for version $(node -p "require('./package.json').version")"
# 4. Push changes (npm version already created the tag)
git push origin main --tags
# 5. Publish
npm publish
```

### Web Application Example

For a web application:

```bash
# Generate a user-friendly "What's New" page
gptchangelog generate --output src/assets/whats-new.md

# Then in your app, you can display this content
# For example, in a React component:
# import WhatsNew from '../assets/whats-new.md';
# function WhatsNewModal() {
#   return <ReactMarkdown>{WhatsNew}</ReactMarkdown>;
# }
```

## Troubleshooting Examples

### Handling Large Repositories

For very large repositories with many commits:

```bash
# Generate changelog for just the last 100 commits
git log -n 100 --pretty=format:"%H" | tail -n 1 | xargs -I{} gptchangelog generate --since {}

# Generate changelog for the last month
ONE_MONTH_AGO=$(git log --since="1 month ago" --pretty=format:"%H" | tail -n 1)
gptchangelog generate --since $ONE_MONTH_AGO
```

### Fixing Version Detection

If version detection isn't working as expected:

```bash
# Manually specify the current version
gptchangelog generate --current-version 1.5.0

# Create a tag if you don't have one
git tag -a v1.0.0 -m "Initial release"
gptchangelog generate
```

### Error Recovery

If you encounter an error during generation:

```bash
# Enable debug mode
export GPTCHANGELOG_DEBUG=1
gptchangelog generate

# Try with a different model
gptchangelog generate --model gpt-3.5-turbo

# Process in smaller batches
git tag v1.0.0-temp
gptchangelog generate --since v1.0.0 --to v1.0.0-temp
git tag -d v1.0.0-temp
```

## Complete Workflow Examples

### Full Release Workflow Example

```bash
#!/bin/bash
# Complete release script

# Ensure we're on the main branch
git checkout main
git pull

# Determine the next version based on changes
PREV_VERSION=$(git describe --tags --abbrev=0)
echo "Previous version was $PREV_VERSION"

# Generate changelog and extract version
CHANGELOG=$(gptchangelog generate --dry-run)
NEXT_VERSION=$(echo "$CHANGELOG" | grep -m 1 "## \[" | sed -r 's/## \[(.*)\].*/\1/')
echo "Next version will be $NEXT_VERSION"

# Update version in files
# (This depends on your project type)
sed -i "s/__version__ = .*/__version__ = '$NEXT_VERSION'/" project/__init__.py

# Generate and save the changelog
gptchangelog generate --current-version $NEXT_VERSION

# Commit the changes
git add CHANGELOG.md project/__init__.py
git commit -m "Release $NEXT_VERSION"

# Create a tag
git tag -a "v$NEXT_VERSION" -m "Release $NEXT_VERSION"

# Push changes and tag
git push origin main
git push origin "v$NEXT_VERSION"

echo "Released version $NEXT_VERSION"
```

### GitHub Action Workflow Example

`.github/workflows/release.yml`:

```yaml
name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install gptchangelog
      
      - name: Get previous tag
        id: previoustag
        run: |
          echo "PREVIOUS_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^ || git rev-list --max-parents=0 HEAD)" >> $GITHUB_ENV
      
      - name: Generate release notes
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          gptchangelog generate --since ${{ env.PREVIOUS_TAG }} --to ${{ github.ref_name }} --output RELEASE_NOTES.md
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
          files: |
            *.tar.gz
            *.zip
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
