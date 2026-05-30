# Repository Guidelines

## Project Structure & Module Organization
This repository is currently documentation-first. All project material lives under `docs/`.

- `docs/NN-*.md`: ordered top-level documents for vision, architecture, flows, and roadmap.
- `docs/architecture/`: diagrams and architecture decision records.
- `docs/ontology/`: entities, relations, rules, and examples for the semantic model.
- `docs/prompts/`: prompt templates for planning, development, and review.
- `docs/research/`: benchmarking and reference material.

Keep new files close to the domain they describe. Follow the existing numeric prefix pattern for top-level docs when order matters, for example `12-api-strategy.md`.

## Build, Test, and Development Commands
There is no committed application build, test, or package manifest yet. Current work is centered on authoring and reviewing Markdown.

- `rg --files docs`: list tracked documentation files quickly.
- `Get-Content docs\README.md`: open the docs index from the terminal.
- `git diff -- docs`: review documentation changes before committing.

If a future toolchain is introduced, document its commands here and in `docs/README.md`.

## Coding Style & Naming Conventions
Write Markdown with short sections, clear headings, and compact bullet lists. Prefer UTF-8 encoding and keep line length readable.

- Use lowercase, hyphenated file names such as `fluxo-de-consulta.md`.
- Preserve the existing Portuguese naming style unless a directory clearly uses English already.
- Use fenced code blocks for commands and structured examples.

## Testing Guidelines
There is no automated test suite yet. Treat review as document validation:

- verify heading hierarchy is consistent;
- check internal paths and filenames before referencing them;
- review diffs for accidental whitespace or encoding issues.

When adding executable code later, add a dedicated test directory and document the exact command to run it.

## Commit & Pull Request Guidelines
Git history currently follows Conventional Commit style, for example `feat: documentação inicial do projeto Brain4me`. Continue using prefixes like `feat:`, `docs:`, `chore:`, and `refactor:`.

Pull requests should include a short summary, the reason for the change, affected document paths, and screenshots only when a rendered diagram or visual artifact changes. Link related issues or planning notes when available.
