#!/bin/bash
set -e

# TerraSmart .deb package build script
# Author: Fernando Reyes (@poeticguy)

VERSION="0.1.0"
PACKAGE_NAME="terrasmart"
MAINTAINER="Fernando Reyes <poeticguy@github.com>"
DESCRIPTION="Natural language to Terraform CLI for Cloudflare"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building TerraSmart .deb package v${VERSION}${NC}"

# Check if we're in the right directory
if [ ! -f "../plan.md" ]; then
    echo -e "${RED}Error: Must be run from the deb/ directory${NC}"
    exit 1
fi

# Create build directory
BUILD_DIR="build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}"

echo -e "${YELLOW}Cleaning previous build...${NC}"
rm -rf "${BUILD_DIR}"
mkdir -p "${PACKAGE_DIR}"

# Create directory structure
mkdir -p "${PACKAGE_DIR}/usr/bin"
mkdir -p "${PACKAGE_DIR}/usr/share/terrasmart/templates"
mkdir -p "${PACKAGE_DIR}/usr/share/terrasmart/schema"
mkdir -p "${PACKAGE_DIR}/DEBIAN"

echo -e "${YELLOW}Installing Python package...${NC}"
# Create virtual environment and install package
python3 -m venv "${BUILD_DIR}/venv"
source "${BUILD_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install ../apps/cli/

# Copy the installed terrasmart script
cp "${BUILD_DIR}/venv/bin/terrasmart" "${PACKAGE_DIR}/usr/bin/"

# Make it executable
chmod +x "${PACKAGE_DIR}/usr/bin/terrasmart"

# Copy templates and schema
cp ../templates/* "${PACKAGE_DIR}/usr/share/terrasmart/templates/"
cp ../schema/* "${PACKAGE_DIR}/usr/share/terrasmart/schema/"

# Create DEBIAN control file
cat > "${PACKAGE_DIR}/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 TerraSmart is a CLI tool that converts natural language descriptions
 into Terraform configurations for Cloudflare infrastructure.
 .
 Features:
  - Natural language to Terraform conversion using OpenAI
  - Support for Cloudflare Workers, DNS records, KV namespaces, D1 databases
  - Secure credential management
  - Automatic terraform execution
Homepage: https://github.com/poeticguy/terrasmart
EOF

# Create postinst script
cp postinst.sh "${PACKAGE_DIR}/DEBIAN/postinst"
chmod +x "${PACKAGE_DIR}/DEBIAN/postinst"

# Create prerm script
cat > "${PACKAGE_DIR}/DEBIAN/prerm" << 'EOF'
#!/bin/bash
# Pre-removal script for terrasmart

echo "Removing TerraSmart..."
# Clean up any temporary files if needed
rm -rf /tmp/terrasmart-* 2>/dev/null || true

exit 0
EOF
chmod +x "${PACKAGE_DIR}/DEBIAN/prerm"

echo -e "${YELLOW}Building .deb package...${NC}"

# Try to use dpkg-deb first, then fpm as fallback
if command -v dpkg-deb >/dev/null 2>&1; then
    echo "Using dpkg-deb..."
    dpkg-deb --build "${PACKAGE_DIR}" "${BUILD_DIR}/"
    DEB_FILE="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}.deb"
elif command -v fpm >/dev/null 2>&1; then
    echo "Using fpm..."
    fpm -s dir -t deb \
        -n "${PACKAGE_NAME}" \
        -v "${VERSION}" \
        -m "${MAINTAINER}" \
        --description "${DESCRIPTION}" \
        --url "https://github.com/poeticguy/terrasmart" \
        --license "MIT" \
        --depends "python3 >= 3.10" \
        --depends "python3-pip" \
        --after-install postinst.sh \
        --package "${BUILD_DIR}/" \
        -C "${PACKAGE_DIR}" \
        usr/
    DEB_FILE="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_all.deb"
else
    echo -e "${RED}Error: Neither dpkg-deb nor fpm found. Please install one of them.${NC}"
    echo "Ubuntu/Debian: sudo apt-get install dpkg-dev"
    echo "Or install fpm: gem install fpm"
    exit 1
fi

# Verify the package was created
if [ -f "${DEB_FILE}" ]; then
    echo -e "${GREEN}✅ Package built successfully!${NC}"
    echo -e "${GREEN}📦 ${DEB_FILE}${NC}"
    
    # Show package info
    echo -e "\n${YELLOW}Package information:${NC}"
    dpkg-deb --info "${DEB_FILE}"
    
    echo -e "\n${YELLOW}Package contents:${NC}"
    dpkg-deb --contents "${DEB_FILE}"
    
    echo -e "\n${GREEN}To install: sudo dpkg -i ${DEB_FILE}${NC}"
    echo -e "${GREEN}To remove: sudo apt-get remove ${PACKAGE_NAME}${NC}"
else
    echo -e "${RED}❌ Package build failed!${NC}"
    exit 1
fi
