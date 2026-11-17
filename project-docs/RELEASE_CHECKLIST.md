# Release checklist

One-time setup (done by the maintainer, not by CI)
- PyPI: trusted publisher for repo `mohdzain98/gnost`, workflow `release.yml`, environment `pypi`.
- TestPyPI: same, environment `testpypi`.
- GitHub environments `pypi`, `testpypi`, `npm` (add required reviewers on `pypi` if wanted).
- npm: placeholders published (`packaging/npm-placeholders/PUBLISH.md`), then per package: trusted publisher = repo `mohdzain98/gnost`, workflow `release.yml`, environment `npm`.
- GHCR: after the first image push, set the `gnost` package visibility to public.
- Branch protection on `main`: require `test (3.9..3.12)`, `other-os (windows-2022)`, `other-os (macos-15)`, `installed-package`.
- After the first successful OIDC PyPI publish: delete the old `PYPI_API_TOKEN` secret.

Each release
1. Branch `release/X.Y.Z` from `dev`; set `__version__` in `gnost/__init__.py` (the only place).
2. Update `CHANGELOG.md`; run `pytest`, `ruff check .`.
3. Dry run: tag `vX.Y.ZrcN` (for example `v0.5.0rc1`). This publishes to TestPyPI, npm `next`, Docker `rc`, and a GitHub pre-release. `release.yml` has a Windows gate: a final tag fails if the Windows tests fail; a release candidate skips the Windows npm package instead. Fix anything that fails, then repeat with the next `rc`.
4. Merge the PR to `main`, set the final version, tag `vX.Y.Z`.
5. Watch the `Release` run, then the `verify` job. Every channel must report `gnost X.Y.Z`.
6. If a publish step failed, re-run the failed jobs; publishing is idempotent (PyPI skips existing files, npm and the release upload skip what exists).
7. The `Verify installs` workflow also runs weekly against the latest PyPI release.
