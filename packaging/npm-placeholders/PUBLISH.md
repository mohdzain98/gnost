# Reserve the npm names (do this yourself, with 2FA)

```
npm login
cd packaging/npm-placeholders
for d in gnost-cli gnost-cli-darwin-arm64 gnost-cli-linux-x64 gnost-cli-win32-x64 gnost-cli-darwin-x64 gnost-cli-linux-arm64; do
  (cd $d && npm publish --access public)   # asks for your 2FA code each time
done
```

If npm rejects a name as too similar to an existing package, tell me and we pick another.
