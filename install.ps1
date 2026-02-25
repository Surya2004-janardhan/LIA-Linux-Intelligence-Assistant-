# WIA (Windows Intelligence Assistant) - Installer for Windows
# This script sets up the Python environment and installs dependencies.

echo "=========================================="
echo "   WIA: Windows Intelligence Assistant   "
echo "           Setup & Installer             "
echo "=========================================="

# 1. Check Python version
$pythonVersion = python --version 2>$null
if ($null -eq $pythonVersion) {
    echo "❌ Python not found. Please install Python 3.10+ from https://python.org"
    exit
}
echo "✅ Found Python: $pythonVersion"

# 2. Create Virtual Environment
if (!(Test-Path -Path ".venv")) {
    echo "📦 Creating virtual environment (.venv)..."
    python -m venv .venv
} else {
    echo "✅ Virtual environment already exists."
}

# 3. Install Dependencies
echo "🛠️  Installing dependencies..."
& .\.venv\Scripts\pip.exe install -r requirements.txt

# 4. Check for winget/choco (Optional)
$winget = Get-Command winget -ErrorAction SilentlyContinue
$choco = Get-Command choco -ErrorAction SilentlyContinue

if ($winget) {
    echo "✅ winget detected (PackageAgent will use it)."
} elseif ($choco) {
    echo "✅ Chocolatey detected (PackageAgent will use it)."
} else {
    echo "⚠️  No system package manager (winget/choco) detected."
    echo "   PackageAgent will be limited to pip/npm."
}

# 5. Setup Configuration
if (!(Test-Path -Path "config\config.yaml")) {
    echo "⚙️  Initializing config.yaml..."
    if (Test-Path -Path "config\config.yaml.example") {
        Copy-Item config\config.yaml.example config\config.yaml
    } else {
        echo "⚠️  config.yaml.example not found. Creating a basic config..."
        New-Item -ItemType Directory -Force -Path config
        "@
llm:
  provider: ollama
  model: llama3
security:
  sandbox_enabled: false
  risk_threshold: HIGH_RISK
@" | Out-File -FilePath config\config.yaml
    }
}

echo ""
echo "🎉 WIA Setup Complete!"
echo "To start WIA, run: .\.venv\Scripts\python.exe wia.py"
echo "=========================================="
