#!/bin/bash

# Ensure the script stops on the first error
set -e

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required to run this deployment script." >&2
    exit 1
fi

echo "Ensuring release dependencies are installed..."
uv sync --dev --extra release

# Variables
#VERSION=$1

# Check if version number is provided
#if [ -z "$VERSION" ]; then
#    echo "Usage: $0 <version>"
#    exit 1
#fi
#
## Update version in setup.py
#echo "Updating version to $VERSION in setup.py..."
## Use awk for cross-platform compatibility
#awk -v version="$VERSION" '/version=/ {gsub(/"[0-9.]+"/, "\"" version "\"")}1' setup.py > setup.tmp && mv setup.tmp setup.py
#
## Install required tools
#echo "Installing twine..."
#pip install --upgrade twine

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist

# Build the package
echo "Building the package with uv..."
uv build

# Upload to PyPI
echo "Uploading the package to PyPI..."
uv run twine upload dist/*

echo "Deployment complete. Version $VERSION has been uploaded to PyPI."
