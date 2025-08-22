#!/bin/bash
# Post-installation script for TerraSmart
# Author: Fernando Reyes (@poeticguy)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 TerraSmart installation completed!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Run: ${BLUE}terrasmart init${NC}"
echo -e "   This will set up your OpenAI and Cloudflare API keys"
echo ""
echo -e "2. Verify installation: ${BLUE}terrasmart doctor${NC}"
echo -e "   This will check all requirements"
echo ""
echo -e "3. Try a dry run: ${BLUE}terrasmart dryrun \"Create a Worker for api.example.com\"${NC}"
echo ""
echo -e "${YELLOW}Requirements:${NC}"
echo -e "• OpenAI API key (required)"
echo -e "• Cloudflare API token and Account ID"
echo -e "• Terraform >= 1.5"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo -e "• GitHub: https://github.com/poeticguy/terrasmart"
echo -e "• Issues: https://github.com/poeticguy/terrasmart/issues"
echo ""
echo -e "${GREEN}Happy infrastructure coding! 🌍${NC}"

exit 0
