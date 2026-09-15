# Agent integrations — Track 2 (tool = truth).
#
# Third-party agent suites (skills + MCP servers) that upstream owns and updates. Installed
# with the vendor's own tool; never vendored into the Track 1 chezmoi source (dot_claude/skills)
# and never touched by `make skills-deploy`.
#
# Independence: every target below is idempotent and per-agent, so a machine that has only
# Claude Code (or only Hermes, or neither) runs just the half it can — nothing hard-requires
# both agents. Re-running is a no-op: an existing MCP entry is left untouched instead of
# re-adding it (which would prompt "Overwrite?" and change nothing anyway).
# Binaries are overridable: CLAUDE=/path/to/claude HERMES=/path/to/hermes.
#
# Recipe + approval model: docs/agents/cloudflare.md

.PHONY: agents-cloudflare agents-cloudflare-claude agents-cloudflare-hermes agents-cloudflare-update

CLAUDE ?= claude
HERMES ?= hermes
CLOUDFLARE_SKILLS := cloudflare/skills

agents-cloudflare: ## Install Cloudflare skills + MCP for whichever agents are installed here
	@$(MAKE) --no-print-directory agents-cloudflare-claude
	@$(MAKE) --no-print-directory agents-cloudflare-hermes
	@echo ""
	@echo "Login next: '$(HERMES) mcp login cloudflare' where Hermes is installed;"
	@echo "            Claude Code authenticates on first Cloudflare tool use, then /reload-plugins."

agents-cloudflare-claude: ## Cloudflare skills + MCP for Claude Code only (skips if not installed)
	@if command -v $(CLAUDE) >/dev/null 2>&1; then \
		echo "== Claude Code: marketplace + plugin (skills and the bundled cloudflare MCP server)"; \
		$(CLAUDE) plugin marketplace add $(CLOUDFLARE_SKILLS) && \
		$(CLAUDE) plugin install cloudflare@cloudflare; \
	else \
		echo "== Claude Code: skipped ('$(CLAUDE)' not on PATH)"; \
	fi

agents-cloudflare-hermes: ## Cloudflare skills + MCP for Hermes only (skips if not installed)
	@if ! command -v $(HERMES) >/dev/null 2>&1; then \
		echo "== Hermes: skipped ('$(HERMES)' not on PATH)"; \
	else \
		if command -v npx >/dev/null 2>&1; then \
			echo "== Hermes: skills (canonical copy in ~/.agents/skills, symlinked into \$$HERMES_HOME/skills)"; \
			npx -y skills add $(CLOUDFLARE_SKILLS) --skill '*' --yes --global --agent hermes-agent; \
		else \
			echo "== Hermes: skills skipped (node/npx not available)"; \
		fi; \
		if $(HERMES) mcp list 2>/dev/null | grep -q cloudflare; then \
			echo "== Hermes: cloudflare MCP already registered — left unchanged"; \
		else \
			echo "== Hermes: cloudflare MCP server (OAuth; write tools stay behind the approval surface)"; \
			$(HERMES) mcp add cloudflare --url https://mcp.cloudflare.com/mcp --auth oauth; \
		fi; \
		if grep -q 'trust: untrusted' $${HERMES_HOME:-$$HOME/.hermes}/config.yaml 2>/dev/null; then \
			echo "   approval gate: OK ('trust: untrusted' present)"; \
		else \
			echo "   ! approval gate: add 'trust: untrusted' to the mcp_servers.cloudflare entry (docs/agents/cloudflare.md)"; \
		fi; \
	fi

agents-cloudflare-update: ## Refresh the Cloudflare skills + Claude plugin to their latest versions
	@if command -v $(CLAUDE) >/dev/null 2>&1; then \
		echo "== Claude Code: refresh marketplace + plugin"; \
		$(CLAUDE) plugin marketplace update cloudflare && \
		$(CLAUDE) plugin install cloudflare@cloudflare; \
		echo "   then: /reload-plugins inside Claude Code"; \
	else \
		echo "== Claude Code: skipped ('$(CLAUDE)' not on PATH)"; \
	fi
	@if command -v npx >/dev/null 2>&1; then \
		echo "== Hermes skills: 'npx skills update -g -y' (local scope holds only the Cloudflare skills)"; \
		npx -y skills update -g -y; \
	else \
		echo "== Hermes skills: skipped (node/npx not available)"; \
	fi
	@echo ""
	@echo "The MCP server itself needs no update: it is remote (Cloudflare's side)."
	@echo "Restart the gateway afterwards so MCP discovery re-runs: '$(HERMES) gateway restart'."
