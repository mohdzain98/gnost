# GNOST — Code Knowledge Scanner

GNOST scans a codebase and reports lines of code by language, folder, and file.

## Installation

```bash
pip install gnost
```

## Usage

```bash
gnost summary [path]
gnost stats [path]
gnost folders [path]
gnost files [path] --top 10
```

## Commands

- `summary`  Show a summary table (default report)
- `stats`    Show detailed stats per language
- `folders`  Show LOC grouped by folder
- `files`    Show the largest files by LOC
- `version`  Display gnost version

## Options

- `--include`  Comma-separated folder names to include (only these are scanned)
- `--exclude`  Comma-separated folder names to exclude (e.g. node_modules,dist)
- `--top`      Number of files to show with `files` (default: 5)
- `--version`  Show version and exit
- `--help`     Show help

## Examples

```bash
gnost summary .
gnost stats src
gnost folders --exclude node_modules,dist
gnost files . --top 20
```

## License

MIT
