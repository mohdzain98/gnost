# Release checklist

One-time setup (done by the maintainer, not by CI)
- PyPI: trusted publisher for repo `mohdzain98/gnost`, workflow `release.yml`, environment `pypi`.
- TestPyPI: same, environment `testpypi`.
- GitHub environments `pypi`, `testpypi`, `npm`, `maven` (add required reviewers on `pypi` if wanted).
- npm: `gnost-cli` org created, placeholders published (`packaging/npm-placeholders/PUBLISH.md`), then per package (`gnost-cli` and each `@gnost-cli/<platform>`): trusted publisher = repo `mohdzain98/gnost`, workflow `release.yml`, environment `npm`.
- Maven Central: Sonatype Central Portal account, namespace `io.github.mohdzain98` verified (via GitHub), a user token, and a GPG key (private key armored, public key on keyserver.ubuntu.com). Secrets in the `maven` environment: `MAVEN_CENTRAL_USERNAME`, `MAVEN_CENTRAL_PASSWORD` (the Portal user token), `MAVEN_GPG_PRIVATE_KEY`, `MAVEN_GPG_PASSPHRASE`.
- GHCR: after the first image push, set the `gnost` package visibility to public.
- Branch protection on `main`: require `test (3.9..3.12)`, `other-os (windows-2022)`, `other-os (macos-15)`, `installed-package`.
- After the first successful OIDC PyPI publish: delete the old `PYPI_API_TOKEN` secret.

Each release
1. Branch `release/X.Y.Z` from `dev`; set `__version__` in `gnost/__init__.py` (the only place).
2. Update `CHANGELOG.md`; run `pytest`, `ruff check .`.
3. Dry run: tag `vX.Y.ZrcN` (for example `v0.5.0rc1`). This publishes to TestPyPI, npm `next`, Docker `rc`, and a GitHub pre-release. `release.yml` has a Windows gate: a final tag fails if the Windows tests fail; a release candidate skips the Windows npm package instead. Fix anything that fails, then repeat with the next `rc`.
4. Merge the PR to `main`, set the final version, tag `vX.Y.Z`.
5. Maven goes last and is never published by CI. A release candidate's Portal upload is validated only; press Drop on it yourself (the Portal API refused the job's drop call with 401, so it is not automatic). For the final tag, open https://central.sonatype.com/publishing/deployments after the `publish-maven` job and press Publish. Published versions cannot be deleted.
5a. Watch the `Release` run, then the `verify` job. Every channel must report `gnost X.Y.Z`.
6. To skip Maven for a release that does not touch the plugin, set the repository variable `SKIP_MAVEN=true` before tagging and delete it afterwards.
7. If a publish step failed, re-run the failed jobs; publishing is idempotent (PyPI skips existing files, npm and the release upload skip what exists).
8. The `Verify installs` workflow also runs weekly against the latest PyPI release.
