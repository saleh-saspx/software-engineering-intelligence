#!/usr/bin/env bash
# Rebuilds the Maven layout from a shallow copy. Sources are stored as
# files/java/<package>/X.java and files/test-java/<package>/X.java (package
# directories named with dots) because the fixture's real depth exceeds what
# some file-transfer tools accept.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
cp "$here/files/README.md" "$here/files/pom.xml" .
place() {
  for pkg in "$here/files/$1"/*/; do
    name="$(basename "$pkg")"
    dest="$2/${name//.//}"
    mkdir -p "$dest"
    cp "$pkg"*.java "$dest/"
  done
}
place java src/main/java
place test-java src/test/java
mkdir -p src/main/resources
cp "$here/files/resources/"* src/main/resources/
