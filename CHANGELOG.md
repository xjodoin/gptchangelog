```markdown
## [v0.8.0] - 2025-03-10

### ✨ Features
- Add logo in PNG and SVG formats for branding consistency and enhanced project visibility
- Simplify deployment script by removing setuptools and wheel installation, using `python -m build` for package building
- Enhance changelog generation by loading meta prompts from template files for improved clarity and structure
- Add `load_meta_prompt` function to read template files for dynamic prompt generation
- Enhance user feedback in CLI by replacing logger with rich console for better visibility

### 🐛 Bug Fixes
- Correct `rich` package version constraint from '=>' to '>=' for proper installation

### 🔄 Changes
- Improve changelog generation process with user confirmation for suggested version

### 📚 Documentation
- Add API reference documentation to improve usability
- Update README to enhance clarity, structure, and formatting of features and instructions

### 🔧 Maintenance
- Create `python-package.yml` for CI configuration
- Remove logo from documentation and configuration for a cleaner presentation
```

**v0.7.0 - 2024-10-29**

- **Features**
  - Replaced logger with rich console in `cli.py` to enhance user feedback and visibility.
  - Introduced user confirmation for suggested version in changelog generation and loaded meta prompts from templates in `openai_utils.py` for better clarity.
  - Added `load_meta_prompt` function in `utils.py` to enable dynamic prompt generation from template files.

- **Bug Fixes**
  - Corrected the version constraint for the rich library in `setup.cfg` from '=>' to '>=' to ensure proper installation.

## [0.6.0] - 2024-10-18

### Added
- Added deploy script and implemented project-specific configuration support for `gptchangelog`.
- Introduced utility functions for fetching commit messages to streamline changelog generation.
- Added functions for rendering prompts and estimating token usage to optimize OpenAI API calls.

### Changed
- Refactored main application logic to improve structure and error handling.
- Enhanced interactions for generating changelogs and versioning, optimizing accuracy and reliability.
- Updated README with additional features, installation, and usage instructions.
- Updated requirements and setup for better package management, removed deprecated `setup.py`, and reorganized project structure for clarity and maintainability.

## [0.5.1] - 2024-05-16

### Added
- Add progress output for batch processing in changelog generation.

### Changed
- Enhance README.md with features, installation, and usage details.

## [0.5.0] - 2024-05-16

### Changed
- Enhanced commit message structure.
- Updated installation instructions for gptchangelog.

## [v0.4.0] - 2023-11-22
### Changed
- Refactor code, improve commit message generation, and changelog wording.

## [v0.3.0] - 2023-11-22

### Changed
- Refactor changelog template
- Update package versions, template headers, and function refactoring

## [0.2.0] - 2023-04-14
### Changed
- Refactor changelog and version prompt templates

## [0.1.1] - 2023-04-13
### Bug Fixes
- Fix deploy

## [0.1.0] - 2023-04-13
### Added
- Initial release

