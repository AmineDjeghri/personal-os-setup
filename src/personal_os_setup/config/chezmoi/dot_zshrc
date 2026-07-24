# Unified .zshrc for macOS and Linux (with/without CUDA)

# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# ============================================================================
# OS Detection
# ============================================================================
if [[ "$OSTYPE" == "darwin"* ]]; then
  export IS_MACOS=true
  export IS_LINUX=false
else
  export IS_MACOS=false
  export IS_LINUX=true
fi

# Ensure local user binaries are found
export PATH="$HOME/.local/bin:$PATH"

# Oh My Zsh
export ZSH="$HOME/.oh-my-zsh" # Path to your oh-my-zsh installation.
ZSH_THEME="powerlevel10k/powerlevel10k" # Set name of the theme to load
zstyle ':omz:update' mode auto      # update automatically without asking


HIST_STAMPS="mm/dd/yyyy"

# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Add wisely, as too many plugins slow down shell startup.
plugins=(git
        dirhistory
        history
        colored-man-pages
        jsontools
        zsh-autocomplete
        zsh-autosuggestions
        zsh-syntax-highlighting
        fzf-zsh-plugin
        )

source $ZSH/oh-my-zsh.sh

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# ============================================================================
# PATH Configuration
# ============================================================================

# Paths for MacOS
if [ "$IS_MACOS" = true ]; then
  # macOS-specific paths (Homebrew, Cryptexes)
  export PATH="/opt/homebrew/bin:/System/Cryptexes/App/usr/bin:$PATH"
  # PyCharm - Only if installed
  if [ -d "/Applications/PyCharm.app/Contents/MacOS" ]; then
    export PATH="/Applications/PyCharm.app/Contents/MacOS:$PATH"
  fi
  # PostgreSQL - Only if installed (Homebrew)
  if [ -d "/usr/local/opt/postgresql@17/bin" ]; then
    export PATH="/usr/local/opt/postgresql@17/bin:$PATH"
  elif [ -d "/opt/homebrew/opt/postgresql@17/bin" ]; then
    export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
  fi
fi

# ============================================================================
# NVM (Node Version Manager) - Only if installed
# ============================================================================
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  . "$NVM_DIR/nvm.sh"  # This loads nvm
  [ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
fi

# ============================================================================
# Rust/Cargo - Only if installed
# ============================================================================
if [ -f "$HOME/.cargo/env" ]; then
  . "$HOME/.cargo/env"
fi

# ============================================================================
# CUDA - Only if installed (typically Linux only)
# ============================================================================
if [ -d "/usr/local/cuda/bin" ]; then
  export PATH=/usr/local/cuda/bin:$PATH
fi

if [ -d "/usr/local/cuda/lib64" ]; then
  export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
fi

if [ "$IS_LINUX" = true ]; then
  # Check for NVIDIA GPU (CUDA availability indicator)
  if command -v nvidia-smi &> /dev/null; then
    export HAS_CUDA=true
  else
    export HAS_CUDA=false
  fi
fi

# ============================================================================
# UV - Only if installed
# ============================================================================
if command -v uv >/dev/null 2>&1; then
  alias python="uv run python"
  alias python3="uv run python"
  # Completions for uv
  eval "$(uv generate-shell-completion zsh)"
fi

# ============================================================================
# Aliases for both MacOS and Linux. For a full list of active aliases, run `alias`.
# ============================================================================
alias zshrc="pycharm -e ~/.zshrc"
if command -v bat >/dev/null 2>&1; then
  alias cat="bat"
  export MANROFFOPT="-c"
  export MANPAGER="sh -c 'col -bx | bat -l man -p'"
fi
if command -v eza >/dev/null 2>&1; then
  alias ls='eza -a --icons --group-directories-first'
  alias ll='eza -la --icons --group-directories-first --header --git'
  alias lt='eza -a --tree --icons --level=2 --group-directories-first'
  alias l.="eza -a | grep -e '^\.'"
fi
if command -v journalctl >/dev/null 2>&1; then
  alias jctl="journalctl -p 3 -xb"
fi
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

backup() {
  cp "$1" "$1.bak"
}
if command -v btop >/dev/null 2>&1; then
  alias top="btop"
fi
if command -v duf >/dev/null 2>&1; then
  alias df="duf"
fi
if command -v dua >/dev/null 2>&1; then
  alias du="dua"
  alias dui="dua i" # interactive TUI mode
fi
# fd is packaged as `fd` on Arch/CachyOS/macOS, but as `fdfind` on Debian/Ubuntu.
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
  alias fd="fdfind"
fi
# zoxide - smarter `cd` that learns your habits
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init zsh)"
fi

# ============================================================================
# fastfetch - system info summary shown on shell startup (interactive shells only)
# ============================================================================
if [[ $- == *i* ]] && command -v fastfetch >/dev/null 2>&1; then
  fastfetch
fi

# ============================================================================
# Auto-activate Python venv - Only if .venv exists in current directory
# ============================================================================
autoload -U add-zsh-hook

_auto_activate_venv() {
  # Only check current directory for .venv
  if [[ -f ".venv/bin/activate" ]]; then
    # Only activate if not already in this venv
    if [[ "$VIRTUAL_ENV" != "$PWD/.venv" ]]; then
      source .venv/bin/activate
    fi
  fi
  # Note: We don't deactivate if no .venv is found
  # This allows you to keep your venv active when navigating
}

add-zsh-hook chpwd _auto_activate_venv
_auto_activate_venv  # Run once on shell startup
