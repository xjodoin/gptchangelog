# Validated generation pipeline

The former opt-in “enhanced” path is now the only generation pipeline. No
`--enhanced` switch is required.

The current implementation:

- validates and resolves the Git range before provider access;
- includes the root commit for untagged repositories;
- determines semantic versions locally;
- makes at most one strict structured model request;
- requires one schema property per source commit, fixes its category with an
  enum, and assigns it to a bounded shared topic, making omission, duplication,
  and cross-category movement structurally impossible;
- assigns categories and renders English, French, or Spanish Markdown locally;
- rejects malformed or duplicate output;
- exposes normalized entry-to-commit provenance in JSON artifacts and the rich
  Python generation result; and
- writes changelogs atomically while preserving `[Unreleased]`.

Use `--stats` for commit statistics, `--quality-analysis` for concrete
validation results, `--format json` for automation, and `--check` to exercise
the complete pipeline without modifying a file.

The hidden `--legacy` argument remains temporarily accepted for command-line
compatibility, but it emits a deprecation notice and runs this same validated
pipeline.
