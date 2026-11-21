#!/usr/bin/env bash
# Prints the download URL of the latest Linux build of a Blender release.
# Usage: bash .github/find-blender.sh 5.3
#
# download.blender.org refuses some GitHub runners with 403 Forbidden, so the
# official mirrors are tried after it. They all keep the same folder layout.
set -u
version="$1"
for site in \
    https://download.blender.org \
    https://mirrors.dotsrc.org/blender \
    https://ftp.nluug.nl/pub/graphics/blender \
    https://mirror.clarkson.edu/blender \
    https://mirrors.ocf.berkeley.edu/blender; do
  base="$site/release/Blender$version"
  file=$(curl -fsSL --retry 2 --retry-all-errors --retry-delay 5 --max-time 60 "$base/" \
    | grep -o 'blender-[0-9.]*-linux-x64\.tar\.xz' | sort -uV | tail -1)
  if [ -n "$file" ]; then
    echo "$base/$file"
    exit 0
  fi
  echo "Blender $version not found on $site, trying the next mirror" >&2
done
echo "No Linux build found for Blender $version" >&2
exit 1
