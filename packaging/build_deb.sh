#!/bin/bash
# LIA .deb Package Builder

set -e

PKG_NAME="lia-linux-intelligence-assistant"
VERSION="1.0.0"
ARCH="all"
BUILD_DIR="lia_build"

echo "Building Debian package for LIA v$VERSION..."

# Clean previous build
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR/DEBIAN
mkdir -p $BUILD_DIR/opt/lia
mkdir -p $BUILD_DIR/usr/bin
mkdir -p $BUILD_DIR/usr/share/applications

# Create control file
cat <<EOF > $BUILD_DIR/DEBIAN/control
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: LIA Team
Depends: python3, python3-pip, firejail, python3-psutil, python3-yaml, python3-requests
Description: Advanced Linux Intelligence Assistant (LIA).
 LIA provides AI-powered system management, safety-guarded automation,
 and self-correcting agent capabilities.
EOF

# Copy source files
cp -r ../* $BUILD_DIR/opt/lia/
rm -rf $BUILD_DIR/opt/lia/.git
rm -rf $BUILD_DIR/opt/lia/.venv
rm -rf $BUILD_DIR/opt/lia/packaging/$BUILD_DIR

# Create symlink
ln -s /opt/lia/lia.py $BUILD_DIR/usr/bin/lia

# Copy desktop entry
cp lia.desktop $BUILD_DIR/usr/share/applications/

# Build package
dpkg-deb --build $BUILD_DIR "${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "Success! Created ${PKG_NAME}_${VERSION}_${ARCH}.deb"
rm -rf $BUILD_DIR
