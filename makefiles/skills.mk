# Agent skills symlink targets.
# Canonical skills live in .claude/skills; .agents/skills holds git symlinks so
# non-Claude agents (Hermes, Codex, OpenCode, skills CLI) see the same files.

.PHONY: skills-link skills-check skills-deploy skills-diff skills-status

CLAUDE_SKILLS := .claude/skills
AGENTS_SKILLS := .agents/skills

# Global deploy: the chezmoi source doubles as the container/CLI deploy source.
SKILLS_SRC := src/personal_os_setup/config/chezmoi/dot_claude/skills
SKILLS_DST := $(HOME)/.claude/skills

# Hermes-only skills: same chezmoi source, separate deploy destination.
HERMES_SKILLS_SRC := src/personal_os_setup/config/chezmoi/dot_hermes/skills
HERMES_SKILLS_DST := $(HOME)/.hermes/skills

skills-link: ## Create/refresh .agents/skills symlinks -> .claude/skills
	@mkdir -p $(AGENTS_SKILLS)
	@# Prune dangling symlinks left behind by deleted skills
	@for l in $(AGENTS_SKILLS)/*; do \
		[ -L "$$l" ] && [ ! -e "$$l" ] && rm -f "$$l" && echo "pruned $$l"; \
	done || true
	@for d in $(CLAUDE_SKILLS)/*/; do \
		[ -d "$$d" ] || continue; \
		name=$${d%/}; name=$${name##*/}; \
		ln -sfn ../../$(CLAUDE_SKILLS)/$$name $(AGENTS_SKILLS)/$$name && echo "linked $$name" || exit 1; \
	done

skills-check: ## Verify every .claude/skills skill has a working .agents/skills symlink
	@rc=0; for d in $(CLAUDE_SKILLS)/*/; do \
		[ -d "$$d" ] || continue; \
		name=$${d%/}; name=$${name##*/}; \
		if [ -L $(AGENTS_SKILLS)/$$name ] && [ -f $(AGENTS_SKILLS)/$$name/SKILL.md ]; then \
			echo "OK   $$name"; \
		else \
			echo "MISS $$name  (run: make skills-link)"; rc=1; \
		fi; \
	done; \
	for l in $(AGENTS_SKILLS)/*; do \
		[ -L "$$l" ] || continue; \
		[ -e "$$l" ] && continue; \
		echo "STALE $$l  (run: make skills-link)"; rc=1; \
	done; exit $$rc

skills-deploy: ## Copy shared skills to ~/.claude/skills and Hermes-only skills to ~/.hermes/skills
	@mkdir -p $(SKILLS_DST)
	@cp -R $(SKILLS_SRC)/. $(SKILLS_DST)/
	@echo "deployed shared skills to $(SKILLS_DST)"
	@mkdir -p $(HERMES_SKILLS_DST)
	@cp -R $(HERMES_SKILLS_SRC)/. $(HERMES_SKILLS_DST)/
	@echo "deployed Hermes-only skills to $(HERMES_SKILLS_DST)"

skills-diff: ## Compare each git-managed skill against its live copy (read-only; exit 1 on drift)
	@rc=0; \
	echo "== shared: $(SKILLS_SRC) -> $(SKILLS_DST)"; \
	for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		if [ ! -e "$(SKILLS_DST)/$$name" ]; then echo "  MISSING  $$name"; rc=1; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" >/dev/null 2>&1; then \
			echo "  DIFFERS  $$name"; diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" | sed 's/^/           /'; rc=1; \
		else echo "  OK       $$name"; fi; \
	done; \
	echo "== hermes-only: $(HERMES_SKILLS_SRC) -> $(HERMES_SKILLS_DST)"; \
	for d in $(HERMES_SKILLS_SRC)/*/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); cat=$$(basename "$$(dirname "$$d")"); \
		if [ ! -e "$(HERMES_SKILLS_DST)/$$cat/$$name" ]; then echo "  MISSING  $$cat/$$name"; rc=1; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(HERMES_SKILLS_DST)/$$cat/$$name" >/dev/null 2>&1; then \
			echo "  DIFFERS  $$cat/$$name"; diff -rq --exclude=.DS_Store "$$d" "$(HERMES_SKILLS_DST)/$$cat/$$name" | sed 's/^/           /'; rc=1; \
		else echo "  OK       $$cat/$$name"; fi; \
	done; \
	exit $$rc

skills-status: ## Show git-managed skills and live copies that duplicate a managed name
	@echo "== git-managed, shared (source: $(SKILLS_SRC))"; \
	for d in $(SKILLS_SRC)/*/; do [ -d "$$d" ] || continue; echo "  shared      $$(basename $$d)"; done; \
	echo "== git-managed, hermes-only (source: $(HERMES_SKILLS_SRC))"; \
	for d in $(HERMES_SKILLS_SRC)/*/*/; do [ -d "$$d" ] || continue; echo "  hermes-only $$(basename $$(dirname "$$d"))/$$(basename $$d)"; done; \
	echo "== live copies duplicating a git-managed name (deploy replaces them; remove the live copy)"; \
	n=0; for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		hit=$$(find $(HERMES_SKILLS_DST) -maxdepth 2 -name "$$name" 2>/dev/null); \
		if [ -n "$$hit" ]; then printf '  DUPLICATE   %s\n' "$$hit"; n=$$((n+1)); fi; \
	done; [ $$n -gt 0 ] || echo "  (none)"; \
	echo "== note: everything else under $(HERMES_SKILLS_DST) is unmanaged (bundled, hub-installed or live-only)"; \
	echo "         list it with: hermes skills list --source local --enabled-only"
