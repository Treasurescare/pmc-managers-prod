#!/bin/bash
# PMC Managers — Capacitor native project scaffolder
# Produces /app/frontend/android and /app/frontend/ios shells
# so .aab (Google Play) and .ipa (App Store) builds are one click away.
#
# Usage: bash /app/scripts/scaffold_native_apps.sh

set -e
cd /app/frontend

echo "==> 1/4  Building production React bundle"
GENERATE_SOURCEMAP=false yarn build

echo "==> 2/4  Adding Android native platform"
if [ ! -d android ]; then
  npx --yes cap add android
else
  echo "   android/ already present — skipping cap add"
fi

echo "==> 3/4  Adding iOS native platform (requires macOS to build/archive)"
if [ ! -d ios ]; then
  npx --yes cap add ios || echo "   (iOS scaffold may fail on non-macOS — safe to ignore until you build in Xcode)"
else
  echo "   ios/ already present — skipping cap add"
fi

echo "==> 4/4  Syncing web build + Capacitor plugins into native projects"
npx --yes cap sync

echo
echo "✅ Done. Next steps:"
echo "   Android: npx cap open android  (requires Android Studio)"
echo "   iOS    : npx cap open ios      (requires Xcode on macOS)"
