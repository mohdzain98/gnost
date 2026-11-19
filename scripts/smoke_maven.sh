#!/usr/bin/env bash
# End-to-end check of the Maven plugin on this machine.
# Usage: scripts/smoke_maven.sh <archive-dir> <version> [github]
# <archive-dir> holds the release archives gnost-<version>-<platform>.tar.gz|zip.
# Builds the plugin with the checksums of those archives, installs it into a throwaway
# local repository, then runs it on a tiny Java project. By default the download comes
# from the folder (file: URL) and the cache is a temporary folder, so nothing leaves this
# machine. With the third argument "github" it downloads from the real GitHub Release.
set -euo pipefail

ARCHIVES="$(cd "$1" && pwd)"
RELEASE="$2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPO="$WORK/m2"
MVNW="$ROOT/packaging/maven/mvnw"

# Same options the release build uses: the release version and each archive's SHA-256.
OPTS="$(python3 "$ROOT/scripts/build_maven.py" "$ARCHIVES" "$RELEASE")"
VERSION="$(cd "$ROOT/packaging/maven" && "$MVNW" -B -q -Dmaven.repo.local="$REPO" help:evaluate -Dexpression=project.version -DforceStdout | tail -1)"
# shellcheck disable=SC2086
(cd "$ROOT/packaging/maven" && "$MVNW" -B -q -Dmaven.repo.local="$REPO" $OPTS install)

SAMPLE="$WORK/sample"
mkdir -p "$SAMPLE/src/main/java/demo"
cat > "$SAMPLE/src/main/java/demo/App.java" <<'JAVA'
package demo;
public class App { public static void main(String[] a) { System.out.println(new Greeter().hi()); } }
JAVA
cat > "$SAMPLE/src/main/java/demo/Greeter.java" <<'JAVA'
package demo;
public class Greeter { String hi() { return "hi"; } }
JAVA

PLUGIN="io.github.mohdzain98:gnost-maven-plugin:$VERSION"
CACHE="$WORK/cache"
cd "$SAMPLE"
MVN=("$MVNW" -B "-Dmaven.repo.local=$REPO" "-Dgnost.home=$CACHE")
if [ "${3:-}" != "github" ]; then MVN+=("-Dgnost.downloadUrl=file://$ARCHIVES"); fi

# A stale gnost first on PATH must be ignored with a warning (the download is used).
mkdir "$WORK/stale"
printf '#!/bin/sh\necho "gnost 0.0.1"\n' > "$WORK/stale/gnost"
chmod +x "$WORK/stale/gnost"
PATH="$WORK/stale:$PATH" "${MVN[@]}" "$PLUGIN:summary" | tee "$WORK/summary.txt"
grep -q "does not match this plugin's version" "$WORK/summary.txt"
grep -q "gnost cache: $CACHE" "$WORK/summary.txt"
grep -q "gnost command: " "$WORK/summary.txt"
grep -q "gnost working directory: " "$WORK/summary.txt"
grep -q "Java" "$WORK/summary.txt"

# No pom.xml here: the plugin must work outside a Maven project. The cache is reused.
"${MVN[@]}" "$PLUGIN:onboard" -Dgnost.depth=2 | tee "$WORK/onboard.txt"
! grep -q "Downloading " "$WORK/onboard.txt"
grep -q "gnost wrote:" "$WORK/onboard.txt"
test -f docs/flow/FLOW-full.mmd
test -f ONBOARD.md

# The help goal lists every goal.
"${MVN[@]}" "$PLUGIN:help" | tee "$WORK/help.txt"
for g in onboard analyze summary help; do grep -q "gnost:$g" "$WORK/help.txt"; done

# A broken mirror must give the install hint instead of a stack trace.
if "${MVN[@]}" "$PLUGIN:summary" "-Dgnost.home=$WORK/empty" "-Dgnost.downloadUrl=file://$WORK/nowhere" > "$WORK/fail.txt" 2>&1; then
  echo "expected the download to fail"; exit 1
fi
grep -q "pipx install gnost" "$WORK/fail.txt"
echo "maven smoke ok ($VERSION)"
