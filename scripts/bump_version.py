#!/usr/bin/env python3
"""
Version bumping script for swytchcode-runtime.

Usage:
    python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1
    python scripts/bump_version.py minor   # 0.1.0 -> 0.2.0
    python scripts/bump_version.py major   # 0.1.0 -> 1.0.0
    python scripts/bump_version.py 1.2.3   # Set to specific version
"""

import re
import sys
from pathlib import Path


def get_current_version():
    """Read current version from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def bump_version(current_version, bump_type):
    """Bump version based on type"""
    parts = list(map(int, current_version.split(".")))
    
    if len(parts) < 3:
        parts.extend([0] * (3 - len(parts)))
    
    if bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    elif bump_type == "patch":
        parts[2] += 1
    else:
        # Assume it's a specific version string
        if re.match(r'^\d+\.\d+\.\d+', bump_type):
            return bump_type
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    return ".".join(map(str, parts))


def update_version(new_version):
    """Update version in pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_path.read_text()
    
    content = re.sub(
        r'^version = ".*"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )
    
    pyproject_path.write_text(content)
    print(f"✓ Updated version to {new_version} in pyproject.toml")


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    current_version = get_current_version()
    new_version = bump_version(current_version, bump_type)
    
    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    
    update_version(new_version)
    
    print("\nNext steps:")
    print("  1. Review changes: git diff pyproject.toml")
    print(f"  2. Commit: git commit -am 'Bump version to {new_version}'")
    print(f"  3. Tag: git tag -a v{new_version} -m 'Release v{new_version}'")
    print("  4. Push: git push origin main --tags")


if __name__ == "__main__":
    main()
