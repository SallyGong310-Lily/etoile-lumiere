#!/bin/zsh
# Build dist/Étoile.app and dist/Lumière.app as thin wrappers around the launchers.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DIST="$ROOT/dist"
VERSION="1.0.0"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Building .app bundles requires macOS." >&2
    exit 1
fi

rm -rf "$DIST"
mkdir -p "$DIST"

build_app() {
    local app_name="$1"        # Étoile
    local exe_name="$2"        # Etoile
    local bundle_id="$3"       # com.etoile.curator
    local icon_src="$4"        # assets/Etoile.icns
    local launcher="$5"        # scripts/etoile_launcher.sh
    local home_var="$6"        # ETOILE_HOME

    local app="$DIST/${app_name}.app"
    mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"

    cp "$icon_src" "$app/Contents/Resources/AppIcon.icns"

    cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>${app_name}</string>
    <key>CFBundleExecutable</key>
    <string>${exe_name}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>${bundle_id}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

    cat > "$app/Contents/MacOS/${exe_name}" <<'WRAPPER'
#!/bin/zsh
# Resolve the repository from dist/<App>.app/Contents/MacOS/<exe>.
MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_BUNDLE="$(cd "$MACOS_DIR/../.." && pwd)"
DIST_DIR="$(cd "$APP_BUNDLE/.." && pwd)"
PROJECT_DIR="${__HOME_VAR__:-$(cd "$DIST_DIR/.." && pwd)}"
export __HOME_VAR__="$PROJECT_DIR"
exec "$PROJECT_DIR/__LAUNCHER__" "$@"
WRAPPER

    sed -i '' -e "s|__HOME_VAR__|${home_var}|g" -e "s|__LAUNCHER__|${launcher}|g" "$app/Contents/MacOS/${exe_name}"

    chmod +x "$app/Contents/MacOS/${exe_name}"
    plutil -lint "$app/Contents/Info.plist" >/dev/null
    codesign --force --deep --sign - "$app" >/dev/null 2>&1 || true
    echo "built: $app"
}

build_app "Étoile"  "Etoile"  "com.etoile.curator"  "assets/Etoile.icns"  "scripts/etoile_launcher.sh"  "ETOILE_HOME"
build_app "Lumière" "Lumiere" "com.lumiere.studio"  "assets/Lumiere.icns" "scripts/lumiere_launcher.sh" "LUMIERE_HOME"

echo
echo "Open with:"
echo "  open \"$DIST/Étoile.app\""
echo "  open \"$DIST/Lumière.app\""
