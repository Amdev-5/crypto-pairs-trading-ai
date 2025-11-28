"""Setup script for pairs trading system"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("ERROR: Python 3.11 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def setup_virtualenv():
    """Create and activate virtual environment"""
    if not os.path.exists("venv"):
        print("\nCreating virtual environment...")
        if not run_command(
            f"{sys.executable} -m venv venv",
            "Creating virtual environment"
        ):
            return False

    print("✓ Virtual environment created")
    return True


def install_python_deps():
    """Install Python dependencies"""
    pip_cmd = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip"

    return run_command(
        f"{pip_cmd} install -r requirements.txt",
        "Installing Python dependencies"
    )


def setup_env_file():
    """Setup .env file"""
    if not os.path.exists(".env"):
        print("\nCreating .env file from template...")

        # Copy .env.example to .env
        with open(".env.example", "r") as src:
            with open(".env", "w") as dst:
                dst.write(src.read())

        print("✓ .env file created")
        print("\n⚠️  IMPORTANT: Edit .env file with your API keys:")
        print("  - BYBIT_API_KEY")
        print("  - BYBIT_API_SECRET")
        print("  - GEMINI_API_KEY")
    else:
        print("✓ .env file already exists")

    return True


def create_directories():
    """Create necessary directories"""
    directories = ["logs", "data", "backtest_results"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

    return True


def setup_dashboard():
    """Setup Next.js dashboard"""
    print("\nSetting up dashboard...")

    os.chdir("dashboard")

    # Check if node is installed
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Node.js not found. Please install Node.js 18+ to use the dashboard")
        os.chdir("..")
        return True  # Not critical, continue

    # Install dependencies
    success = run_command("npm install", "Installing dashboard dependencies")

    os.chdir("..")
    return success


def print_next_steps():
    """Print next steps"""
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)

    print("\n📋 Next Steps:")
    print("\n1. Configure your API keys:")
    print("   Edit .env file with your Bybit and Gemini API keys")

    print("\n2. Test the setup:")
    print("   python -m src.main  # (with TRADING_ENABLED=False)")

    print("\n3. Run backtests:")
    print("   python -m src.backtesting.backtest_engine")

    print("\n4. Start the dashboard:")
    print("   cd dashboard")
    print("   npm run dev")

    print("\n5. When ready for live trading:")
    print("   - Set TRADING_ENABLED=True in .env")
    print("   - Set BYBIT_TESTNET=True for paper trading")
    print("   - Set BYBIT_TESTNET=False for live trading (at your own risk)")

    print("\n⚠️  IMPORTANT WARNINGS:")
    print("   - Start with testnet/paper trading")
    print("   - Use small position sizes initially")
    print("   - Monitor the system closely")
    print("   - Cryptocurrency trading carries significant risk")

    print("\n📚 Documentation:")
    print("   - README.md - Quick start guide")
    print("   - ARCHITECTURE.md - Technical details")
    print("   - config.yaml - Trading parameters")

    print("\n" + "="*60)


def main():
    """Main setup function"""
    print("="*60)
    print("CRYPTO PAIRS TRADING SYSTEM - SETUP")
    print("="*60)

    # Check Python version
    if not check_python_version():
        return 1

    # Setup virtual environment
    if not setup_virtualenv():
        print("ERROR: Failed to create virtual environment")
        return 1

    # Install Python dependencies
    if not install_python_deps():
        print("ERROR: Failed to install Python dependencies")
        return 1

    # Setup .env file
    if not setup_env_file():
        return 1

    # Create directories
    if not create_directories():
        return 1

    # Setup dashboard (optional)
    setup_dashboard()

    # Print next steps
    print_next_steps()

    return 0


if __name__ == "__main__":
    sys.exit(main())
