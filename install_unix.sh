#!/bin/sh
set -e  # Exit on error

echo "📦 Setting up Personal OS Setup..."

if [ "$(uname -s 2>/dev/null)" = "Linux" ]; then
    if ! command -v make >/dev/null 2>&1; then
        echo "🔧 'make' not found. Installing..."
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update
            sudo apt-get install -y make
        else
            echo "❌ Could not determine package manager to install 'make'. Please install it manually and re-run."
            exit 1
        fi
    fi
fi

if ! command -v chezmoi >/dev/null 2>&1; then
    echo "🔧 'chezmoi' not found. Installing..."
    CHEZMOI_BIN_DIR="$HOME/.local/bin"
    mkdir -p "$CHEZMOI_BIN_DIR"
    if command -v curl >/dev/null 2>&1; then
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$CHEZMOI_BIN_DIR"
    elif command -v wget >/dev/null 2>&1; then
        sh -c "$(wget -qO- get.chezmoi.io)" -- -b "$CHEZMOI_BIN_DIR"
    else
        echo "❌ Neither curl nor wget found; cannot install chezmoi automatically. Please install it manually and re-run."
    fi
    case ":$PATH:" in
        *":$CHEZMOI_BIN_DIR:"*) ;;
        *) PATH="$CHEZMOI_BIN_DIR:$PATH" ;;
    esac
fi

REPO_URL="https://github.com/AmineDjeghri/personal-os-setup.git"
FOLDER_NAME="personal-os-setup"
INSTALL_DIR="$HOME/.personal-os-setup"

echo "📦 Checking repository setup..."

REPO_ROOT=""

# If we are already inside an existing git checkout of this repo, use it in place.
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    TOPLEVEL=$(git rev-parse --show-toplevel)
    if [ "$(basename "$TOPLEVEL")" = "$FOLDER_NAME" ]; then
        echo "✅ You are already inside the repository."
        REPO_ROOT="$TOPLEVEL"
    fi
fi

# Otherwise, install/reuse a fixed location in the user's home directory.
if [ -z "$REPO_ROOT" ]; then
    if [ -d "$INSTALL_DIR" ]; then
        echo "✅ Repository found at $INSTALL_DIR. Entering..."
    else
        echo "📂 Repository not found. Cloning into $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    REPO_ROOT="$INSTALL_DIR"
fi

cd "$REPO_ROOT"

echo "⬇️ Pulling..."
git pull
# Log everything to a timestamped file inside .logs/
mkdir -p .logs
LOGFILE=".logs/install_$(date +%Y%m%d_%H%M%S).log"
echo "📝 Logging to: $LOGFILE"

link_command() {
    VENV_BIN="$REPO_ROOT/.venv/bin/personal-os-setup"
    if [ ! -x "$VENV_BIN" ]; then
        return
    fi
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    ln -sf "$VENV_BIN" "$LOCAL_BIN/personal-os-setup"
    echo "🔗 Linked personal-os-setup -> $LOCAL_BIN/personal-os-setup"
    case ":$PATH:" in
        *":$LOCAL_BIN:"*) ;;
        *)
            echo "⚠️  $LOCAL_BIN is not on your PATH. Add it to your shell profile to run 'personal-os-setup' from anywhere:"
            echo "    export PATH=\"$LOCAL_BIN:\$PATH\""
            ;;
    esac
}

# NOTE: The UI requires a real TTY. Piping stdout through `tee` makes stdout a pipe
# and can break terminal ioctls. We only use `tee` for non-interactive steps.
if [ -t 1 ]; then
  make install 2>&1 | tee -a "$LOGFILE"
  link_command

  if command -v script >/dev/null 2>&1; then
    OS_NAME=$(uname -s 2>/dev/null)
    if [ "$OS_NAME" = "Darwin" ]; then
      # macOS: script logfile command [args...]
      script -q -a "$LOGFILE" make run
    else
      # Linux and others: script -c "command" logfile
      script -q -a -c "make run" "$LOGFILE"
    fi
  else
    echo "⚠️  'script' not found; running UI without logging to preserve TTY."
    make run
  fi
else
  {
    make install
    link_command
    make run
  } 2>&1 | tee -a "$LOGFILE"
fi
