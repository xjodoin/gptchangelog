# Release Guide for GPTChangelog

This document describes the automated release process for the GPTChangelog project using the `release.sh` script.

## Overview

The `release.sh` script automates the entire release process, including:

1. **Changelog Generation** - Uses gptchangelog itself to generate a comprehensive changelog
2. **Version Management** - Updates the version number and release date
3. **Git Operations** - Commits changes, creates tags, and pushes to remote
4. **Deployment** - Builds and deploys the package to PyPI

## Prerequisites

Before running the release script, ensure you have:

- [x] **Clean working directory** - All changes must be committed or stashed
- [x] **Valid git repository** - Script must be run from the project root
- [x] **OpenAI API key configured** - Required for changelog generation
- [x] **PyPI credentials configured** - Required for deployment (via twine)
- [x] **Development dependencies installed** - `pip install -e .`

### Environment Setup

1. **Configure OpenAI API Key:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   # Or use gptchangelog config
   gptchangelog config init
   ```

2. **Configure PyPI credentials:**
   ```bash
   # Create ~/.pypirc or use environment variables
   pip install twine
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e .
   pip install build twine
   ```

## Usage

### Basic Release Process

1. **Navigate to project root:**
   ```bash
   cd /path/to/gptchangelog
   ```

2. **Run the release script:**
   ```bash
   ./release.sh
   ```

3. **Follow the interactive prompts:**
   - The script automatically detects the next version from changelog generation
   - Review the changelog generation (interactive mode) 
   - Confirm the release summary with auto-detected version
   - Approve the final deployment

### Example Session

```bash
$ ./release.sh

[INFO] Starting gptchangelog release process...
[INFO] Current version: 0.8.2

[STEP] Generating changelog and extracting next version using gptchangelog...
[SUCCESS] Suggested next version: 0.9.0

[STEP] Generating final changelog interactively...
# Interactive changelog generation with quality analysis...

============================================
           RELEASE SUMMARY
============================================
Project: gptchangelog
Current version: 0.8.2
New version: 0.9.0 (auto-detected)
Release date: 2025-06-04
Git branch: main
Git status: Clean
============================================

This will:
1. Use the generated changelog (already created)
2. Update version to 0.9.0
3. Commit the changes
4. Create git tag v0.9.0
5. Push to remote repository
6. Deploy to PyPI

Do you want to proceed? (y/N): y

[STEP] Updating version to 0.9.0 in gptchangelog/__init__.py
[STEP] Committing changes...
[STEP] Creating git tag v0.9.0...
[STEP] Pushing changes and tags to remote repository...
[STEP] Deploying to PyPI...

============================================
       RELEASE COMPLETED SUCCESSFULLY!
============================================
```

## What the Script Does

### 1. Pre-flight Checks
- Verifies you're in a git repository
- Ensures working directory is clean
- Validates version format (semantic versioning)
- Checks that new version differs from current version

### 2. Changelog Generation
- Uses `gptchangelog generate --interactive --quality-analysis --stats`
- Provides enhanced commit analysis and quality metrics
- Allows interactive editing of the generated changelog
- Shows detailed statistics about commits and changes

### 3. Version Management
- Updates `__version__` in `gptchangelog/__init__.py`
- Updates `__date__` with current release date
- Creates backup files for rollback capability

### 4. Git Operations
- Commits changelog and version updates
- Creates annotated git tag (e.g., `v0.9.0`)
- Pushes commits and tags to remote repository

### 5. Deployment
- Builds the package using `python -m build`
- Uploads to PyPI using `twine upload`
- Verifies successful deployment

### 6. Error Handling & Rollback
- Automatic rollback on any failure
- Restores original files from backups
- Removes created git tags if deployment fails
- Provides clear error messages and recovery instructions

## Features

### 🎨 Colored Output
The script provides color-coded output for better readability:
- 🔵 **INFO**: General information
- 🟢 **SUCCESS**: Successful operations
- 🟡 **WARNING**: Warnings and non-critical issues  
- 🔴 **ERROR**: Errors and failures
- 🔷 **STEP**: Current operation being performed

### 🔄 Interactive Mode
- Automatically detects next version from changelog generation
- Shows comprehensive release summary with auto-detected version
- Requires explicit confirmation before proceeding
- Allows changelog review and editing
- Offers fallback to manual version input if needed

### 📊 Enhanced Changelog Features
The script uses gptchangelog's enhanced mode with:
- **Quality Analysis**: Provides quality metrics and suggestions
- **Commit Statistics**: Shows detailed analysis of changes
- **Interactive Editing**: Allows manual changelog refinement
- **Multi-language Support**: Can generate changelogs in different languages

### 🛡️ Safety Features
- **Clean State Verification**: Ensures no uncommitted changes
- **Version Validation**: Enforces semantic versioning
- **Automatic Rollback**: Reverts changes on failure
- **Backup Creation**: Creates backups before modifications

## Advanced Usage

### Environment Variables

You can customize the script behavior using environment variables:

```bash
# OpenAI Configuration
export OPENAI_API_KEY="your-key"
export GPTCHANGELOG_MODEL="gpt-4"
export GPTCHANGELOG_MAX_TOKENS="80000"

# Custom Editor for Interactive Mode
export EDITOR="code"  # VS Code
export EDITOR="nano"  # Nano editor
```

### Skip Deployment

To test the release process without deploying to PyPI, you can modify the script or comment out the deployment step.

### Custom Deployment

The script uses the existing `deploy.sh` for PyPI deployment. You can modify that script for custom deployment targets.

## Troubleshooting

### Common Issues

1. **"Working directory is not clean"**
   ```bash
   git status
   git add . && git commit -m "Pre-release cleanup"
   # or
   git stash
   ```

2. **"OpenAI API key not configured"**
   ```bash
   export OPENAI_API_KEY="your-key"
   # or
   gptchangelog config init
   ```

3. **"PyPI upload failed"**
   - Check your PyPI credentials
   - Ensure version doesn't already exist
   - Verify package builds correctly

4. **"Git push failed"**
   - Check remote repository access
   - Ensure you have push permissions
   - Verify branch is up to date

### Recovery from Failed Release

If a release fails partway through:

1. **Check what was completed:**
   ```bash
   git log --oneline -5
   git tag -l "v*" | tail -5
   ```

2. **Manual rollback if needed:**
   ```bash
   # Remove local tag
   git tag -d v1.2.3
   
   # Remove remote tag (if pushed)
   git push origin :refs/tags/v1.2.3
   
   # Reset commit (if made)
   git reset --hard HEAD~1
   ```

3. **Clean up and retry:**
   ```bash
   git status
   ./release.sh
   ```

## Security Considerations

- **API Keys**: Ensure OpenAI API keys are properly secured
- **PyPI Credentials**: Use token-based authentication for PyPI
- **Repository Access**: Verify push permissions before release
- **Branch Protection**: Consider using branch protection rules

## Best Practices

1. **Test Before Release**
   - Run tests locally: `python -m pytest`
   - Verify functionality with development install: `pip install -e .`

2. **Review Generated Changelog**
   - Always review the AI-generated changelog
   - Edit for clarity and completeness
   - Ensure all breaking changes are highlighted

3. **Version Strategy**
   - Follow semantic versioning (MAJOR.MINOR.PATCH)
   - Increment MAJOR for breaking changes
   - Increment MINOR for new features
   - Increment PATCH for bug fixes

4. **Release Timing**
   - Release during business hours for quick issue resolution
   - Avoid releases before weekends or holidays
   - Coordinate with team members

## Integration with CI/CD

The release script can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Release
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version'
        required: true

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Run Release
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
        run: |
          echo "${{ github.event.inputs.version }}" | ./release.sh
```

---

For more information about GPTChangelog, see the [main README](README.md) and [documentation](docs/).
