#!/usr/bin/env node
"use strict";
const { spawnSync } = require("child_process");
const { resolveBinary } = require("../lib/resolve");

let exe;
try {
  exe = resolveBinary().exe;
} catch (e) {
  console.error(e.message);
  process.exit(1);
}
const r = spawnSync(exe, process.argv.slice(2), { stdio: "inherit" });
if (r.error) {
  console.error(r.error.message);
  process.exit(1);
}
process.exit(r.status === null ? 1 : r.status);
