"use strict";
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const SUPPORTED = ["darwin-arm64", "linux-x64", "win32-x64"];

// Platform key (process.platform-process.arch) -> npm package name.
// Windows is not called "win32" because npm's spam filter rejected that name.
const PACKAGE_NAMES = {
  "darwin-arm64": "gnost-cli-darwin-arm64",
  "darwin-x64": "gnost-cli-darwin-x64",
  "linux-x64": "gnost-cli-linux-x64",
  "linux-arm64": "gnost-cli-linux-arm64",
  "win32-x64": "gnost-cli-windows-x64",
};

function platformKey(platform = process.platform, arch = process.arch) {
  return `${platform}-${arch}`;
}

function unsupportedMessage(key, supported = SUPPORTED) {
  return (
    `gnost-cli has no prebuilt binary for ${key}.\n` +
    `Supported: ${supported.join(", ")}.\n` +
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
  const checksums = opts.checksums || JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "checksums.json"), "utf8"),
  );
  // checksums.json lists the platforms this release was built for.
  const built = Object.keys(checksums);
  const supported = built.length ? built : SUPPORTED;
  if (!supported.includes(key)) throw new Error(unsupportedMessage(key, supported));
  const pkg = PACKAGE_NAMES[key] || `gnost-cli-${key}`;
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

module.exports = { resolveBinary, platformKey, SUPPORTED, PACKAGE_NAMES };
