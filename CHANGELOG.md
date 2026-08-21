# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [v0.10.1] - 2025-10-01

[Compare changes](https://github.com/xjodoin/gptchangelog/compare/v0.10.0...v0.10.1)
Contributors: Xavier Jodoin

### 🔄 Changes
- Migrate CLI tooling to "uv" / "uvx": standardize how the project is run, tested, and built from the command line to give more consistent behavior across shells and environments.
- Improve command-line UI and prompts: present clearer, more consistent messages and command names so developers can run and debug the project with less guesswork.
- Advise verifying scripts and CI: recommend checking any custom scripts, CI pipelines, or automation that call previous run commands to confirm compatibility with the new "uv"/"uvx" invocations.

### 📚 Documentation
- Expand installation section in README to cover both "uv" and "uvx" usage: make setup instructions clearer and provide recommended invocations per environment and shell.
- Add cross-cutting developer docs: provide more onboarding material and usage guidance across backend, frontend, build, and config areas to reduce setup friction for new contributors and maintainers.
- Centralize build/config instructions: consolidate guidance so developers can find a single, consistent place for build and configuration steps.

### 🔧 Maintenance
- Clean up multi-component build/config details: align small configuration and build details across backend, frontend, and build scripts to improve long-term maintainability.
- Make non-user-facing adjustments that support the "uv"/"uvx" migration and documentation improvements.
- No breaking changes detected; most users do not need to take any action.
- Action recommended for CI / scripts: if you have custom automation that invokes the project directly, quickly verify and update those commands to the "uv"/"uvx" style described in the README. Migration effort is typically low (edit of an invocation or two).
- Where to look: see the updated README and docs for the exact command examples and environment-specific notes.


## [v0.10.0] - 2025-08-11

[Compare changes](https://github.com/xjodoin/gptchangelog/compare/v0.9.0...v0.10.0)
Contributors: Xavier Jodoin

### ✨ Features
- **Enhanced Changelog Generation**: Now supports internationalization (i18n) and additional customization options. Users can generate changelogs with GitHub compare URLs and contributors lists, improving transparency and collaboration. New CLI flags allow toggling features like emojis and custom section orders, providing greater flexibility in presentation.

### 📚 Documentation
- **SEO and Structure Improvements**: Enhanced documentation with improved metadata and structure to boost searchability and organization, making it easier for users to find and navigate content.
- **Template Resilience**: Improved robustness of documentation templates to prevent errors on pages lacking context, such as 404 pages, ensuring a smoother user experience.

### 🔧 Maintenance
- **Build Process Simplification**: Streamlined the build process by removing unnecessary plugins, reducing potential build issues and maintenance overhead.
- **Dependency Management**: Updated and cleaned up dependencies, contributing to a leaner and more efficient build environment, enhancing system stability and performance.


## [v0.9.0] - 2025-06-04

This release of GPTChangelog introduces significant enhancements to the changelog generation process, making it more user-friendly and efficient. Users will benefit from improved automation, documentation, and visualization capabilities.

### ✨ Features  
- **Release Automation**: Streamline your deployment workflow with our new release guide and automation script, reducing manual effort and minimizing errors in the release process.
- **Enhanced Changelog Generation**: Experience more accurate and insightful changelogs thanks to improved commit analysis and AI processing, making it easier to understand project updates.
- **Diagram Support**: Create dynamic and visually engaging documentation with new support for mermaid diagrams, enhancing the clarity and appeal of your project documentation.

### 🐛 Bug Fixes
- **Version Extraction**: Resolved an issue with version number extraction in our release script, ensuring compatibility with various versioning formats and preventing potential deployment errors.

### 📚 Documentation
- **Improved Clarity**: Updated the release guide to provide clearer instructions for changelog generation and user interaction, facilitating smoother contributions and project management.

### 🔧 Maintenance
- **Deployment Preparation**: Enhanced the deployment script to automatically install necessary build dependencies, ensuring a more reliable and seamless deployment process.
- **Code Refactoring**: Simplified version extraction logic in the release script, improving code readability and maintainability for future updates.

These updates collectively enhance the functionality, usability, and reliability of the GPTChangelog project, ensuring a smoother experience for both developers and end-users.
