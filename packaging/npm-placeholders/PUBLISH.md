# Reserve the scoped npm names (do this yourself, with 2FA)

The platform binaries moved from `gnost-cli-<platform>` to the `@gnost-cli/<platform>` scope in 0.5.1.
`gnost-cli` itself keeps its name and its trusted publisher.

## Order

1. Create the `gnost-cli` organization on npmjs.com (Add organization, free plan, public packages).
   If the name is taken, tell me and we switch to `@mohdzain98/<platform>`.
2. Publish the five placeholders (each asks for your 2FA code):

```
npm login
cd packaging/npm-placeholders/@gnost-cli
for d in darwin-arm64 linux-x64 windows-x64 darwin-x64 linux-arm64; do
  (cd $d && npm publish --access public)
done
```

3. For each of the five packages, open its Settings > Trusted Publisher on npmjs.com and add:
   GitHub Actions, owner `mohdzain98`, repository `gnost`, workflow `release.yml`, environment `npm`.
   (`gnost-cli` already has this; the three real ones are required, the other two are for later.)
4. Release 0.5.1 (the pipeline publishes the three real packages, then `gnost-cli`).
5. After 0.5.1 is on `latest`, deprecate the old unscoped packages (see below).

## Deprecate the old unscoped packages (run only after 0.5.1 is live)

```
npm deprecate gnost-cli-darwin-arm64 "Moved to @gnost-cli/darwin-arm64"
npm deprecate gnost-cli-linux-x64 "Moved to @gnost-cli/linux-x64"
npm deprecate gnost-cli-windows-x64 "Moved to @gnost-cli/windows-x64"
npm deprecate gnost-cli-darwin-x64 "Moved to @gnost-cli/darwin-x64"
npm deprecate gnost-cli-linux-arm64 "Moved to @gnost-cli/linux-arm64"
```

The older `gnost-cli@0.5.0` still depends on the unscoped names, so leave those packages published.

## The main package placeholder

`gnost-cli/` here was only the first reservation; it is already published and needs nothing more.
