# Agent skills symlink targets.
# Canonical repo-scoped skills live in .claude/skills; .agents/skills holds git symlinks so
# non-Claude agents (Hermes, Codex, OpenCode, skills CLI) see the same files.
# Global skills: ONE authored tree (SKILLS_SRC) deployed to ~/.claude/skills. Hermes reads that
# dir via skills.external_dirs, so a name must never also exist under ~/.hermes/skills
# (`make skills-status` flags it). Codex gets per-skill links in ~/.agents/skills.
# The list of deliberately saved skills is skills.keep.

.PHONY: skills-link skills-check skills-repo-to-live skills-live-to-repo skills-status _skills-scan skills-thirdparty-live-to-repo skills-thirdparty-repo-to-live

CLAUDE_SKILLS := .claude/skills
AGENTS_SKILLS := .agents/skills

# Global deploy: the chezmoi source doubles as the container/CLI deploy source.
SKILLS_SRC := src/personal_os_setup/config/chezmoi/dot_claude/skills
SKILLS_DST := $(or $(CLAUDE_CONFIG_DIR),$(HOME)/.claude)/skills
SKILLS_CODEX_DST ?= $(HOME)/.agents/skills
SKILLS_PYTHON ?= python3
SKILLS_SUPPORT := src/personal_os_setup/config/chezmoi/dot_claude/skills_support.py
SKILLS_LINK = $(SKILLS_PYTHON) $(SKILLS_SUPPORT) link --source "$(SKILLS_SRC)" --claude "$(SKILLS_DST)" --codex "$(SKILLS_CODEX_DST)"

# Never deploy here: Hermes already reads SKILLS_DST; skills-status flags duplicates.
HERMES_SKILLS_LIVE := $(HOME)/.hermes/skills
SKILLS_KEEP := skills.keep


skills-link: ## Create/refresh .agents/skills symlinks -> .claude/skills
	@printf '%b\n' "${CYAN}=========> skills-link...${NC}" >&2
	@mkdir -p $(AGENTS_SKILLS)
	@# Prune dangling symlinks left behind by deleted skills
	@for l in $(AGENTS_SKILLS)/*; do \
		[ -L "$$l" ] && [ ! -e "$$l" ] && rm -f "$$l" && printf "$(YELLOW)pruned$(NC) $$l\n"; \
	done || true
	@for d in $(CLAUDE_SKILLS)/*/; do \
		[ -d "$$d" ] || continue; \
		name=$${d%/}; name=$${name##*/}; \
		ln -sfn ../../$(CLAUDE_SKILLS)/$$name $(AGENTS_SKILLS)/$$name && printf "$(GREEN)linked$(NC) $$name\n" || exit 1; \
	done
	@printf '%b\n' "${GREEN}skills-link complete${NC}" >&2

skills-check: ## Verify every .claude/skills skill has a working .agents/skills symlink
	@printf '%b\n' "${CYAN}=========> skills-check...${NC}" >&2
	@rc=0; for d in $(CLAUDE_SKILLS)/*/; do \
		[ -d "$$d" ] || continue; \
		name=$${d%/}; name=$${name##*/}; \
		if [ -L $(AGENTS_SKILLS)/$$name ] && [ -f $(AGENTS_SKILLS)/$$name/SKILL.md ]; then \
			printf "$(GREEN)OK  $(NC) $$name\n"; \
		else \
			printf "$(RED)MISS$(NC) $$name  (run: make skills-link)\n"; rc=1; \
		fi; \
	done; \
	for l in $(AGENTS_SKILLS)/*; do \
		[ -L "$$l" ] || continue; \
		[ -e "$$l" ] && continue; \
		printf "$(RED)STALE$(NC) $$l  (run: make skills-link)\n"; rc=1; \
	done; exit $$rc
	@printf '%b\n' "${GREEN}skills-check complete${NC}" >&2

skills-repo-to-live: ## Deploy authored skills repo -> ~/.claude/skills (Claude/Hermes) and link each one for Codex
	@printf '%b\n' "${CYAN}=========> skills-repo-to-live...${NC}" >&2
ifeq ($(SKILLS_FORCE),1)
	@printf "$(YELLOW)skills-repo-to-live: drift check SKIPPED (SKILLS_FORCE=1)$(NC)\n"
else
	@$(MAKE) --no-print-directory _skills-scan SKILLS_SCAN_MODE=drift || { echo; printf "$(RED)skills-repo-to-live: ABORTED$(NC) -- the live copies above differ from git.\n"; echo "Reconcile the live version into git first, or re-run with SKILLS_FORCE=1 to overwrite them."; exit 1; }
endif
	@$(SKILLS_LINK) --preflight
	@mkdir -p "$(SKILLS_DST)"
	@cp -R "$(SKILLS_SRC)/." "$(SKILLS_DST)/"
	@$(SKILLS_LINK)
	@printf "$(GREEN)deployed$(NC) skills to $(SKILLS_DST)\n"
	@printf '%b\n' "${GREEN}skills-repo-to-live complete${NC}" >&2

# Internal scan behind skills-status (mode "all": MISSING or DIFFERS -> exit 1, full OK/DIFFERS/MISSING
# report + Codex link check) and the skills-repo-to-live gate (mode "drift": DIFFERS only -> exit 1;
# MISSING is fine, i.e. never deployed yet).
_skills-scan:
	@printf '%b\n' "${CYAN}=========> _skills-scan...${NC}" >&2
	@rc=0; \
	[ "$$SKILLS_SCAN_MODE" = "all" ] && printf "$(CYAN)== $(SKILLS_SRC) -> $(SKILLS_DST)$(NC)\n"; \
	for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		if [ ! -e "$(SKILLS_DST)/$$name" ]; then \
			[ "$$SKILLS_SCAN_MODE" = "all" ] && { printf "  $(YELLOW)MISSING$(NC)  $$name\n"; rc=1; }; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" >/dev/null 2>&1; then \
			printf "  $(RED)DIFFERS$(NC)  $$name\n"; diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" | sed 's/^/           /'; rc=1; \
		elif [ "$$SKILLS_SCAN_MODE" = "all" ]; then printf "  $(GREEN)OK$(NC)       $$name\n"; fi; \
	done; \
	if [ "$$SKILLS_SCAN_MODE" = "drift" ]; then \
		if [ $$rc -ne 0 ]; then printf "$(RED)drift check: DRIFT found$(NC) (live differs from git; see DIFFERS above)\n"; \
		else printf "$(GREEN)drift check: no drift$(NC) (live copies match git, or are not yet deployed)\n"; fi; \
	fi; \
	exit $$rc
	@if [ "$$SKILLS_SCAN_MODE" = all ]; then $(SKILLS_LINK) --check; else $(SKILLS_LINK) --preflight; fi
	@printf '%b\n' "${GREEN}_skills-scan complete${NC}" >&2

skills-status: ## One read-only report: repo vs live copies, Codex links, Hermes name clashes, skills missing from skills.keep, third-party lock/content
	@printf '%b\n' "${CYAN}=========> skills-status...${NC}" >&2
	@rc=0; \
	$(MAKE) --no-print-directory _skills-scan SKILLS_SCAN_MODE=all || rc=1; \
	printf "$(CYAN)== names in BOTH $(SKILLS_DST) and $(HERMES_SKILLS_LIVE) (Hermes reads both: unloadable -- remove the ~/.hermes copy)$(NC)\n"; \
	n=0; for d in $(SKILLS_DST)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		hit=$$(find $(HERMES_SKILLS_LIVE) -maxdepth 2 -name "$$name" 2>/dev/null); \
		if [ -n "$$hit" ]; then printf '  $(RED)DUPLICATE$(NC)   %s\n' "$$hit"; n=$$((n+1)); fi; \
	done; [ $$n -gt 0 ] && rc=1 || printf "  $(GREEN)(none)$(NC)\n"; \
	printf "$(CYAN)== repo skills missing from $(SKILLS_KEEP)$(NC)\n"; \
	m=0; for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		if ! grep -v '^[[:space:]]*#' $(SKILLS_KEEP) 2>/dev/null | grep -qx "$$name"; then printf "  $(YELLOW)UNLISTED$(NC)    $$name\n"; m=$$((m+1)); fi; \
	done; [ $$m -gt 0 ] && rc=1 || printf "  $(GREEN)(none)$(NC)\n"; \
	printf "$(CYAN)== third-party skills ($(TARGET_AGENTS))$(NC)\n"; \
	if [ -f "$(LIVE_SKILLS_LOCK)" ]; then \
		$(SKILLS_PYTHON) $(SKILLS_SUPPORT) verify --lock "$(THIRD_PARTY_LOCK)" --live-lock "$(LIVE_SKILLS_LOCK)" --agents "$(TARGET_AGENTS)" --claude "$(SKILLS_DST)" --codex "$(SKILLS_CODEX_DST)" --receipts "$(SKILLS_RECEIPTS)" || rc=1; \
	else echo "  (no live lock at $(LIVE_SKILLS_LOCK) -- nothing installed via npx here)"; fi; \
	exit $$rc
	@printf '%b\n' "${GREEN}skills-status complete${NC}" >&2

skills-live-to-repo: ## Save a live skill into the repo: make skills-live-to-repo NAME=<name> (copies ~/.claude/skills/<name>, lists it in skills.keep)
	@printf '%b\n' "${CYAN}=========> skills-live-to-repo...${NC}" >&2
	@test -n "$(NAME)" || { printf "$(RED)usage:$(NC) make skills-live-to-repo NAME=<name>\n"; exit 1; }
	@test -d "$(SKILLS_DST)/$(NAME)" || { printf "$(RED)skills-live-to-repo: no live skill$(NC) at $(SKILLS_DST)/$(NAME)\n"; exit 1; }
	@mkdir -p "$(SKILLS_SRC)/$(NAME)"
	@cp -R "$(SKILLS_DST)/$(NAME)/." "$(SKILLS_SRC)/$(NAME)/"
	@touch $(SKILLS_KEEP)
	@grep -qxF "$(NAME)" $(SKILLS_KEEP) || echo "$(NAME)" >> $(SKILLS_KEEP)
	@printf "$(GREEN)kept$(NC) $(NAME): $(SKILLS_SRC)/$(NAME) + $(SKILLS_KEEP)\n"
	@printf '%b\n' "${GREEN}skills-live-to-repo complete${NC}" >&2

# ── Third-party skills (npx skills) ────────────────────────────────────────────────────────────
# `npx skills` is the mechanism for third-party SKILLS-ONLY packs. Its lock lives OUTSIDE any repo
# (a global install: $(XDG_STATE_HOME)/skills/.skill-lock.json on current CLIs, $(HOME)/.agents/.skill-lock.json
# on older ones), so the committed COPY below is what
# makes a new machine rebuildable. The copy deliberately does NOT sit in the chezmoi source: a
# `chezmoi apply` must never overwrite the tool's live lock with a stale record.
#
# Lock identities and installed content are checked by src/personal_os_setup/config/chezmoi/dot_claude/skills_support.py.
# Local content receipts are separate from the CLI lock and never committed.
THIRD_PARTY_LOCK := third-party-skills.lock.json
XDG_STATE := $(or $(XDG_STATE_HOME),$(HOME)/.local/state)
# First existing wins (XDG first); if neither exists, point at the XDG path so the error names where it should be.
LIVE_SKILLS_LOCK ?= $(firstword $(wildcard $(XDG_STATE)/skills/.skill-lock.json $(HOME)/.agents/.skill-lock.json) $(XDG_STATE)/skills/.skill-lock.json)
JQ_TP_NAMES := .skills | keys[]

AGENTS ?= claude-code codex
# AGENT remains a compatible single-agent override.
TARGET_AGENTS = $(if $(strip $(AGENT)),$(AGENT),$(AGENTS))
SKILLS_RECEIPTS ?= $(XDG_STATE)/personal-os-setup/skills-installed.json

skills-thirdparty-live-to-repo: ## Copy the live npx lock into the repo (the record we ship)
	@printf '%b\n' "${CYAN}=========> skills-thirdparty-live-to-repo...${NC}" >&2
	@test -f "$(LIVE_SKILLS_LOCK)" || { printf '$(RED)no live lock$(NC) at %s\n' "$(LIVE_SKILLS_LOCK)"; exit 1; }
	@jq . "$(LIVE_SKILLS_LOCK)" > "$(THIRD_PARTY_LOCK)"  # jq also adds the trailing newline the end-of-file hook requires
	@printf '$(GREEN)recorded$(NC) %s -- %s entries\n' "$(THIRD_PARTY_LOCK)" "$$(jq -r '$(JQ_TP_NAMES)' $(THIRD_PARTY_LOCK) | wc -l | tr -d ' ')"
	@printf '%b\n' "${GREEN}skills-thirdparty-live-to-repo complete${NC}" >&2

# The replay logic lives in ONE script shared with chezmoi (run_after_ in the same dir).
THIRD_PARTY_REPLAY := src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh

skills-thirdparty-repo-to-live: ## Install and verify third-party skills for AGENTS (default Claude + Codex)
	@printf '%b\n' "${CYAN}=========> skills-thirdparty-repo-to-live...${NC}" >&2
	@AGENTS="$(TARGET_AGENTS)" LOCK="$(abspath $(THIRD_PARTY_LOCK))" SKILLS_DST="$(SKILLS_DST)" SKILLS_CODEX_DST="$(SKILLS_CODEX_DST)" SKILLS_PYTHON="$(SKILLS_PYTHON)" LIVE_SKILLS_LOCK="$(LIVE_SKILLS_LOCK)" SKILLS_RECEIPTS="$(SKILLS_RECEIPTS)" FORCE=1 STRICT=1 bash $(THIRD_PARTY_REPLAY)
	@printf '%b\n' "${GREEN}skills-thirdparty-repo-to-live complete${NC}" >&2
