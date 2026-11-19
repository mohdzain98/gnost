"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { resolveBinary, platformKey } = require("../lib/resolve");

function fakePackage(key, content) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gnost-npm-"));
  const name = key.startsWith("win32") ? "gnost.exe" : "gnost";
  fs.mkdirSync(path.join(dir, "bundle"));
  fs.writeFileSync(path.join(dir, "bundle", name), content);
  fs.writeFileSync(path.join(dir, "package.json"), "{}");
  return path.join(dir, "package.json");
}

test("platform key joins platform and arch", () => {
  assert.strictEqual(platformKey("linux", "x64"), "linux-x64");
});

test("unsupported platform lists supported ones and alternatives", () => {
  assert.throws(() => resolveBinary({ key: "freebsd-x64", checksums: {} }), /Supported: darwin-arm64, linux-x64, win32-x64[\s\S]*pipx[\s\S]*Docker/);
});

test("missing platform package explains optional dependencies", () => {
  const resolver = () => { throw new Error("nope"); };
  assert.throws(() => resolveBinary({ key: "linux-x64", resolver, checksums: {} }), /--no-optional/);
});

test("checksum mismatch is rejected", () => {
  const pj = fakePackage("linux-x64", "binary");
  assert.throws(
    () => resolveBinary({ key: "linux-x64", resolver: () => pj, checksums: { "linux-x64": "00" } }),
    /Checksum mismatch/,
  );
});

test("matching checksum resolves the executable", () => {
  const pj = fakePackage("win32-x64", "binary");
  const sum = require("crypto").createHash("sha256").update("binary").digest("hex");
  const r = resolveBinary({ key: "win32-x64", resolver: () => pj, checksums: { "win32-x64": sum } });
  assert.ok(r.exe.endsWith("gnost.exe"));
});

test("a platform missing from this release's checksums is reported as unsupported", () => {
  assert.throws(
    () => resolveBinary({ key: "win32-x64", checksums: { "linux-x64": "ab" } }),
    /no prebuilt binary for win32-x64[\s\S]*Supported: linux-x64/,
  );
});

test("Windows maps to the @gnost-cli/windows-x64 package", () => {
  const { PACKAGE_NAMES } = require("../lib/resolve");
  assert.strictEqual(PACKAGE_NAMES["win32-x64"], "@gnost-cli/windows-x64");
  let asked;
  const resolver = (p) => { asked = p; throw new Error("nope"); };
  assert.throws(() => resolveBinary({ key: "win32-x64", resolver, checksums: {} }), /@gnost-cli\/windows-x64/);
  assert.strictEqual(asked, "@gnost-cli/windows-x64/package.json");
});
