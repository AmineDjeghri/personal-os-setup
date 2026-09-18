# Agent skills symlink targets.
# Canonical skills live in .claude/skills; .agents/skills holds git symlinks so
# non-Claude agents (Hermes, Codex, OpenCode, skills CLI) see the same files.

.PHONY: skills-link skills-check skills-deploy

CLAUDE_SKILLS := .claude/skills
AGENTS_SKILLS := .agents/skills

# Global deploy: the chezmoi source doubles as the container/CLI deploy source.
SKILLS_SRC := src/personal_os_setup/config/chezmoi/dot_claude/skills
SKILLS_DST := $(HOME)/.claude/skills

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

skills-deploy: ## Copy shared skills from the chezmoi source to ~/.claude/skills (both agents read this dir)
	@mkdir -p $(SKILLS_DST)
	@cp -R $(SKILLS_SRC)/. $(SKILLS_DST)/
	@echo "deployed shared skills to $(SKILLS_DST)"
