# Agent integrations — Track 2 (tool = truth).
#
# Third-party agent suites (skills + MCP servers) that are owned and updated upstream.
# Installed with the vendor's own tool; never vendored into the Track 1 chezmoi source
# (dot_claude/skills) and never touched by `make skills-deploy`.
#
# Recipe + approval model: docs/agents/cloudflare.md

.PHONY: agents-cloudflare agents-cloudflare-check

CLAUDE ?= claude
HERMES ?= hermes
CLOUDFLARE_SKILLS := cloudflare/skills

agents-cloudflare: ## Install Cloudflare skills + MCP server for Claude Code and Hermes
	@command -v $(CLAUDE) >/dev/null || { echo "claude not on PATH (set CLAUDE=/path/to/claude)"; exit 1; }
	@command -v $(HERMES) >/dev/null || { echo "hermes not on PATH (set HERMES=/path/to/hermes)"; exit 1; }
	@echo "== Claude Code: marketplace + plugin (skills and the bundled cloudflare MCP server)"
	$(CLAUDE) plugin marketplace add $(CLOUDFLARE_SKILLS)
	$(CLAUDE) plugin install cloudflare@cloudflare
	@echo "== Hermes: skills (canonical copy in ~/.agents/skills, symlinked into \$$HERMES_HOME/skills)"
	npx -y skills add $(CLOUDFLARE_SKILLS) --skill '*' --yes --global --agent hermes-agent
	@echo "== Hermes: cloudflare MCP server (OAuth; write tools stay behind the approval surface)"
	$(HERMES) mcp add cloudflare --url https://mcp.cloudflare.com/mcp --auth oauth
	@echo
	@echo "Next steps:"
	@echo "  1. ensure the mcp_servers.cloudflare entry carries 'trust: untrusted' (docs/agents/cloudflare.md)"
	@echo "  2. $(HERMES) mcp login cloudflare    # browser OAuth; restart the agent afterwards"
	@echo "  3. Claude Code: /reload-plugins to activate the plugin"

agents-cloudflare-check: ## Verify the Cloudflare wiring is present and approval-gated
	@$(HERMES) mcp list 2>/dev/null | grep -q cloudflare && echo "OK   hermes: cloudflare MCP registered" || echo "MISS hermes: cloudflare MCP (run: make agents-cloudflare)"
	@grep -q 'trust: untrusted' $$(echo $${HERMES_HOME:-$$HOME/.hermes}/config.yaml) 2>/dev/null && echo "OK   hermes: untrusted trust tier" || echo "WARN hermes: no 'trust: untrusted' found in config.yaml"
	@[ -d "$${CLAUDE_CONFIG_DIR:-$$HOME/.claude}/plugins" ] && ls "$${CLAUDE_CONFIG_DIR:-$$HOME/.claude}/plugins/marketplaces" 2>/dev/null | grep -q cloudflare && echo "OK   claude: cloudflare marketplace registered" || echo "MISS claude: cloudflare marketplace (run: make agents-cloudflare)"
	@[ -n "$$(ls -d $${HERMES_HOME:-$$HOME/.hermes}/skills/*cloudflare* 2>/dev/null)" ] && echo "OK   hermes: cloudflare skills linked" || echo "MISS hermes: cloudflare skills (run: make agents-cloudflare)"
