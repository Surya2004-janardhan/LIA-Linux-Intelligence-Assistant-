#!/usr/bin/env bash
# LIA — Linux Intelligence Agent Installer
# curl -sSL https://raw.githubusercontent.com/your-username/LIA/main/install.sh | bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   LIA — Linux Intelligence Agent      ║${NC}"
echo -e "${CYAN}║   \"Linux is flexible down to the OS\"  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo -e "${RED}Warning: LIA is designed for Linux systems.${NC}"
    echo "This script may fail on other platforms."
    echo -n "Continue anyway? [y/N] "
    read -r choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3.10+ is required but not found.${NC}"
    # Try to install if possible
    if command -v apt-get &> /dev/null; then
        echo "Attempting to install python3..."
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python python-pip
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip
    else
        echo "Please install Python 3 manually."
        exit 1
    fi
fi

# Check systemd/journalctl
if command -v journalctl &> /dev/null; then
    echo -e "${GREEN}✓${NC} systemd detected (logs enabled)"
else
    echo -e "${CYAN}ℹ${NC} systemd not found. Some log features may be limited."
fi

# Clone or update
if [ -d "LIA" ]; then
    echo -e "${CYAN}→${NC} Updating LIA..."
    cd LIA
    git pull --quiet
else
    echo -e "${CYAN}→${NC} Cloning LIA..."
    git clone --quiet https://github.com/your-username/LIA.git
    cd LIA
fi

# Virtual Environment (recommended for Linux)
if [ ! -d "venv" ]; then
    echo -e "${CYAN}→${NC} Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
echo -e "${CYAN}→${NC} Installing dependencies..."
pip install --upgrade pip --quiet
pip install -e . --quiet

# Create data directories
mkdir -p memory workflows

# Check Ollama
echo ""
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓${NC} Ollama found"
    if ! ollama list 2>/dev/null | grep -q "llama3"; then
        echo -e "${CYAN}→${NC} Pulling llama3 model..."
        ollama pull llama3
    else
        echo -e "${GREEN}✓${NC} llama3 model ready"
    fi
else
    echo -e "${CYAN}ℹ${NC} Ollama not found. Install: curl -fsSL https://ollama.com/install.sh | sh"
fi

# Add alias with VENV activation
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then SHELL_RC="$HOME/.zshrc"; elif [ -f "$HOME/.bashrc" ]; then SHELL_RC="$HOME/.bashrc"; fi

if [ -n "$SHELL_RC" ]; then
    LIA_CMD="source $(pwd)/venv/bin/activate && python3 $(pwd)/lia.py"
    if ! grep -q "alias lia=" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# LIA — Linux Intelligence Agent" >> "$SHELL_RC"
        echo "alias lia='$LIA_CMD'" >> "$SHELL_RC"
        echo -e "${GREEN}✓${NC} Added 'lia' alias to ${SHELL_RC}"
    else
        echo -e "${GREEN}✓${NC} 'lia' alias detected"
    fi
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation Complete!               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo "  Run:"
echo "    source venv/bin/activate"
echo "    lia status"
echo "    lia ask \"restart nginx and show logs\""
echo ""
