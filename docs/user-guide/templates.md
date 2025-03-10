# Prompt Templates

GPTChangelog uses customizable prompt templates to guide the AI in generating high-quality changelogs. This page explains how these templates work and how you can customize them.

## Understanding Templates

GPTChangelog uses three main prompt templates:

1. **Commits Template** (`commits_prompt.txt`): Guides the processing and refinement of commit messages
2. **Version Template** (`version_prompt.txt`): Determines the next version number based on semantic versioning
3. **Changelog Template** (`changelog_prompt.txt`): Formats the final changelog output

These templates use Python's `string.Template` format with `$variable` placeholders.

## Default Templates

### Commits Template

This template helps the AI understand and process raw commit messages:

```
Commit Messages:
```
$commit_messages
```

Objective:

To enhance a series of commit messages by merging redundant information and improving clarity.

Instructions:
1. Input Collection:
    Gather all provided commit messages.
    Ensure the messages are complete and accurate for processing.

...
```

### Version Template

This template determines the next version number based on semantic versioning:

```
Task: Increment Software Version Number Using Semantic Versioning

Current Version: $latest_version (format: MAJOR.MINOR.PATCH)

Commit Messages:
```
$commit_messages
```

Rules for Incrementing:
    MAJOR Update: Increment for incompatible API changes.
    MINOR Update: Increment for new, backwards-compatible functionality.
    PATCH Update: Increment for backwards-compatible bug fixes.

...
```

### Changelog Template

This template formats the final changelog:

```
Changelog Generation for Software Project (Version: $next_version)

Date: $current_date

Commit Messages:
```
$commit_messages
```

Objective:
Create a structured, clear, and concise changelog in markdown format, reflecting the changes made in the latest software version.

Instructions:
1. Format the Changelog Header:
    Use markdown's ## syntax to format the version header.
    Follow the pattern: ## [$next_version] - $current_date.

...
```

## Customizing Templates

You can customize these templates to fit your project's specific needs.

### Template Location

The default templates are located in the GPTChangelog package. To customize them, create your own copies in a project-specific location:

```
.gptchangelog/templates/
├── changelog_prompt.txt
├── commits_prompt.txt
└── version_prompt.txt
```

GPTChangelog will look for templates in this directory before falling back to the defaults.

### Available Variables

Each template has access to specific variables:

#### Commits Template
- `$commit_messages`: The raw commit messages
- `$project_name`: The name of your project

#### Version Template
- `$commit_messages`: The processed commit messages
- `$latest_version`: The current version number
- `$project_name`: The name of your project

#### Changelog Template
- `$commit_messages`: The processed commit messages
- `$next_version`: The determined next version number
- `$current_date`: The current date (YYYY-MM-DD)
- `$project_name`: The name of your project

### Example Customization

Here's an example of a customized changelog template:

```
# $project_name Changelog

## Release $next_version (Released on $current_date)

The following changes were included in this release:

$commit_messages

### Breaking Changes

List any breaking changes here.

### Known Issues

- None at this time

### Contributors

Thanks to all our contributors for this release!
```

## Template Best Practices

When customizing templates, consider the following best practices:

1. **Be Specific**: Give clear instructions to the AI
2. **Structure Matters**: Organize your template with clear sections
3. **Consistent Formatting**: Maintain a consistent style guide
4. **Test Thoroughly**: Test your templates with different types of commits
5. **Preserve Variables**: Don't remove the essential variables needed for template rendering

## Advanced Template Techniques

### Custom Categorization

You can customize how changes are categorized:

```
Categorize changes into these custom groups:
- User-Facing: Changes visible to end users
- Backend: Internal changes not visible to users
- Performance: Optimizations and speed improvements
- Security: Security fixes and enhancements
- Documentation: Documentation and example updates
```

### Project-Specific Instructions

Add project-specific context:

```
This project is a Python CLI tool for data analysis.
When describing changes, focus on:
- Command usage changes
- Data processing improvements
- User experience enhancements
```

### Custom Formatting

Specify your preferred Markdown formatting:

```
Use the following format for the changelog:
# Release $next_version

**Release Date**: $current_date

## What's New
- Feature 1
- Feature 2

## Bug Fixes
- Fix 1
- Fix 2
```

## Troubleshooting Templates

If you encounter issues with custom templates:

1. **Syntax Errors**: Ensure your template uses the correct `$variable` syntax
2. **Missing Variables**: Make sure all required variables are present
3. **Template Not Found**: Verify the template file paths and names
4. **Unexpected Output**: Check for formatting issues or conflicting instructions

For debugging, you can run with the dry-run option to see the rendered output without saving:

```bash
gptchangelog generate --dry-run
```