#!/usr/bin/env bash
# End-to-end check of the Maven channel on this machine.
# Usage: scripts/smoke_maven.sh <binary-zip-dir>
# Builds the modules with the zips from build_maven.py, installs them into a
# throwaway local repository, then runs the plugin on a tiny Java project.
set -euo pipefail

ZIPS="$(cd "$1" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPO="$WORK/m2"
MVNW="$ROOT/packaging/maven/mvnw"

DEST="$ROOT/packaging/maven/gnost-binary/binaries"
mkdir -p "$DEST"
if [ "$ZIPS" != "$(cd "$DEST" && pwd)" ]; then cp "$ZIPS"/*.zip "$DEST/"; fi
VERSION="$(cd "$ROOT/packaging/maven" && "$MVNW" -B -q -Dmaven.repo.local="$REPO" help:evaluate -Dexpression=project.version -DforceStdout | tail -1)"
(cd "$ROOT/packaging/maven" && "$MVNW" -B -q -Dmaven.repo.local="$REPO" install)

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
cd "$SAMPLE"
# No pom.xml here: the plugin must work outside a Maven project.
MVN=("$MVNW" -B -q "-Dmaven.repo.local=$REPO")
"${MVN[@]}" "$PLUGIN:summary" | tee "$WORK/summary.txt"
grep -q "Java" "$WORK/summary.txt"
"${MVN[@]}" "$PLUGIN:onboard" -Dgnost.depth=2
test -f docs/flow/FLOW-full.mmd
test -f ONBOARD.md || test -d docs
echo "maven smoke ok ($VERSION)"
