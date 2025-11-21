#!/bin/bash
# Build script for Hugo blog with Gemini support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Building Hugo Blog ==="

cd "$PROJECT_DIR"

# Build Hugo site
echo "Building Hugo site..."
hugo --minify

# Build Gemini version
echo ""
echo "=== Building Gemini Version ==="
python3 "$SCRIPT_DIR/md2gemini.py"

echo ""
echo "=== Build Complete ==="
echo "Hugo output: public/"
echo "Gemini output: public_gemini/"
