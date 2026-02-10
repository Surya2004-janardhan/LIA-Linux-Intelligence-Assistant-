#!/usr/bin/env bash
# LIA Installer — One-liner: curl -sSL https://raw.githubusercontent.com/your-username/LIA/main/install.sh | bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   LIA — Local Intelligence Agent      ║${NC}"
echo -e "${CYAN}║   Privacy-first AI OS wrapper          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3.10+ is required but not found.${NC}"
    echo "Install: https://www.python.org/downloads/"
    exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓${NC} Python ${PYVER} found"

# Check pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip not found.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} pip found"

# Clone or update
if [ -d "LIA" ]; then
    echo -e "${CYAN}→${NC} Updating existing LIA installation..."
    cd LIA
    git pull --quiet
else
    echo -e "${CYAN}→${NC} Cloning LIA..."
    git clone --quiet https://github.com/your-username/LIA.git
    cd LIA
fi

# Install dependencies
echo -e "${CYAN}→${NC} Installing dependencies..."
pip install -e . --quiet 2>/dev/null || pip3 install -e . --quiet 2>/dev/null

# Create data directories
mkdir -p memory workflows

# Check Ollama
echo ""
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓${NC} Ollama found"
    if ! ollama list 2>/dev/null | grep -q "llama3"; then
        echo -e "${CYAN}→${NC} Pulling llama3 model (this may take a few minutes)..."
        ollama pull llama3
    else
        echo -e "${GREEN}✓${NC} llama3 model ready"
    fi
else
    echo -e "${CYAN}ℹ${NC} Ollama not found. Install for local LLM: https://ollama.ai"
    echo "  LIA also supports OpenAI/Groq — configure in config.yaml"
fi

# Add alias
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias lia=" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# LIA — Local Intelligence Agent" >> "$SHELL_RC"
        echo "alias lia='python3 $(pwd)/lia.py'" >> "$SHELL_RC"
        echo -e "${GREEN}✓${NC} Added 'lia' alias to ${SHELL_RC}"
    else
        echo -e "${GREEN}✓${NC} 'lia' alias already exists"
    fi
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation complete!               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo "  Quick start:"
echo "    lia ask \"check my disk space\""
echo "    lia explain \"tar -czf backup.tar.gz .\""
echo "    lia status"
echo "    lia help"
echo ""
echo "  Or restart your shell and run: lia help"
