"use strict";
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const SUPPORTED = ["darwin-arm64", "linux-x64", "win32-x64"];

function platformKey(platform = process.platform, arch = process.arch) {
  return `${platform}-${arch}`;
}

function unsupportedMessage(key) {
  return (
    `gnost-cli has no prebuilt binary for ${key}.\n` +
    `Supported: ${SUPPORTED.join(", ")}.\n` +
    `Use "pipx install gnost" or the Docker image ghcr.io/mohdzain98/gnost instead.`
  );
}

function missingMessage(pkg) {
  return (
    `The platform package ${pkg} is not installed.\n` +
    `This happens when optional dependencies are skipped (--no-optional or --omit=optional).\n` +
    `Reinstall gnost-cli with optional dependencies enabled.`
  );
}

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

// Returns {exe} or throws Error with a user-facing message.
function resolveBinary(opts = {}) {
  const key = opts.key || platformKey();
  if (!SUPPORTED.includes(key)) throw new Error(unsupportedMessage(key));
  const pkg = `gnost-cli-${key}`;
  const resolver = opts.resolver || ((p) => require.resolve(p, { paths: [__dirname] }));
  let pkgJson;
  try {
    pkgJson = resolver(`${pkg}/package.json`);
  } catch (e) {
    throw new Error(missingMessage(pkg));
  }
  const exeName = key.startsWith("win32") ? "gnost.exe" : "gnost";
  const exe = path.join(path.dirname(pkgJson), "bundle", exeName);
  if (!fs.existsSync(exe)) throw new Error(missingMessage(pkg));
  const checksums = opts.checksums || JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "checksums.json"), "utf8"),
  );
  const expected = checksums[key];
  if (expected) {
    const actual = sha256File(exe);
    if (actual !== expected) {
      throw new Error(
        `Checksum mismatch for ${pkg}: the installed binary does not match this gnost-cli release.\n` +
          `Reinstall gnost-cli.`,
      );
    }
  }
  return { exe };
}

module.exports = { resolveBinary, platformKey, SUPPORTED };
