#!/bin/bash
# WIA .deb Package Builder

set -e

PKG_NAME="WIA-linux-intelligence-assistant"
VERSION="1.0.0"
ARCH="all"
BUILD_DIR="WIA_build"

echo "Building Debian package for WIA v$VERSION..."

# Clean previous build
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR/DEBIAN
mkdir -p $BUILD_DIR/opt/WIA
mkdir -p $BUILD_DIR/usr/bin
mkdir -p $BUILD_DIR/usr/share/applications

# Create control file
cat <<EOF > $BUILD_DIR/DEBIAN/control
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: WIA Team
Depends: python3, python3-pip, firejail, python3-psutil, python3-yaml, python3-requests
Description: Advanced Linux Intelligence Assistant (WIA).
 WIA provides AI-powered system management, safety-guarded automation,
 and self-correcting agent capabilities.
EOF

# Copy source files
cp -r ../* $BUILD_DIR/opt/WIA/
rm -rf $BUILD_DIR/opt/WIA/.git
rm -rf $BUILD_DIR/opt/WIA/.venv
rm -rf $BUILD_DIR/opt/WIA/packaging/$BUILD_DIR

# Create symlink
ln -s /opt/WIA/WIA.py $BUILD_DIR/usr/bin/WIA

# Copy desktop entry
cp WIA.desktop $BUILD_DIR/usr/share/applications/

# Build package
dpkg-deb --build $BUILD_DIR "${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "Success! Created ${PKG_NAME}_${VERSION}_${ARCH}.deb"
rm -rf $BUILD_DIR
