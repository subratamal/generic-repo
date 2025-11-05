#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CLEAN_BUILD=true

usage() {
    cat <<'EOF'
Usage:
  publish_pypi.sh [--no-clean]

Options:
  --no-clean            Skip deleting existing build artifacts before building.

Environment Variables:
  TWINE_USERNAME / TWINE_PASSWORD or TWINE_API_KEY must be set for authentication.

Example:
  TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... ./scripts/publish_pypi.sh
EOF
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --no-clean)
            CLEAN_BUILD=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

command -v python >/dev/null || { echo "Python is required but not found in PATH" >&2; exit 1; }
python -m build --version >/dev/null 2>&1 || { echo "The 'build' package is required. Install it via 'pip install build'." >&2; exit 1; }
python -m twine --version >/dev/null 2>&1 || { echo "The 'twine' package is required. Install it via 'pip install twine'." >&2; exit 1; }

if [[ "$CLEAN_BUILD" == true ]]; then
    echo "Cleaning previous build artifacts..."
    rm -rf "${REPO_ROOT}/build" "${REPO_ROOT}/dist" "${REPO_ROOT}"/*.egg-info
fi

echo "Building distribution packages..."
python -m build --outdir "${REPO_ROOT}/dist" "${REPO_ROOT}"

echo "Publishing to PyPI..."
python -m twine upload "${REPO_ROOT}/dist"/* --verbose

echo "Package upload completed successfully."

