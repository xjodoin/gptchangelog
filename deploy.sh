#!/bin/bash

# Ensure the script stops on the first error
set -e

# Variables
VERSION=$1

# Check if version number is provided
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# Update version in setup.py
echo "Updating version to $VERSION in setup.py..."
sed -i "s/version=\"[0-9.]*\"/version=\"$VERSION\"/" setup.py

# Install required tools
echo "Installing setuptools, wheel, and twine..."
pip install --upgrade setuptools wheel twine

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist

# Build the package
echo "Building the package..."
python setup.py sdist bdist_wheel

# Upload to PyPI
echo "Uploading the package to PyPI..."
twine upload dist/*

echo "Deployment complete. Version $VERSION has been uploaded to PyPI."

