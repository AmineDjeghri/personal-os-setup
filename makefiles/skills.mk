# Agent skills symlink targets.
# Canonical repo-scoped skills live in .claude/skills; .agents/skills holds git symlinks so
# non-Claude agents (Hermes, Codex, OpenCode, skills CLI) see the same files.
# Global skills: ONE authored tree (SKILLS_SRC) deployed to ~/.claude/skills. Hermes reads that
# dir via skills.external_dirs, so a name must never also exist under ~/.hermes/skills
# (`make skills-status` flags it). Codex gets per-skill links in ~/.agents/skills.
# The list of deliberately saved skills is skills.keep.

.PHONY: skills-link skills-check skills-personal-repo-to-live skills-personal-live-to-repo skills-all-repo-to-live skills-all-live-to-repo skills-status _skills-scan skills-thirdparty-live-to-repo skills-thirdparty-repo-to-live

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

# "repo <time>  live <time>  -> <which is newer>" from the newest file mtime under each dir (args: repo live).
SKILLS_NEWER = $(SKILLS_PYTHON) -c 'import os,sys,time; m=lambda d: max((os.path.getmtime(os.path.join(r,f)) for r,_,fs in os.walk(d) for f in fs if f!=".DS_Store"),default=0); a,b=m(sys.argv[1]),m(sys.argv[2]); g,y,n=sys.argv[3:6]; t=lambda x: time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)); c=lambda x,o: (g if x>o else y if x<o else n); print("repo "+c(a,b)+t(a)+n+"  live "+c(b,a)+t(b)+n+"  -> "+(g+"live is NEWER" if b>a else g+"repo is NEWER" if a>b else "same time")+n)'


skills-link: ## Create/refresh .agents/skills symlinks -> .claude/skills
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

skills-check: ## Verify every .claude/skills skill has a working .agents/skills symlink
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

skills-personal-repo-to-live: ## Deploy personal (authored/modified) skills repo -> ~/.claude/skills (Claude/Hermes) and link each one for Codex
ifeq ($(SKILLS_FORCE),1)
	@printf "$(YELLOW)skills-personal-repo-to-live: drift check SKIPPED (SKILLS_FORCE=1)$(NC)\n"
else
	@$(MAKE) --no-print-directory _skills-scan SKILLS_SCAN_MODE=drift || { echo; printf "$(RED)skills-personal-repo-to-live: ABORTED$(NC) -- the live copies above differ from git.\n"; echo "Reconcile the live version into git first, or re-run with SKILLS_FORCE=1 to overwrite them."; exit 1; }
endif
	@$(SKILLS_LINK) --preflight
	@mkdir -p "$(SKILLS_DST)"
	@cp -R "$(SKILLS_SRC)/." "$(SKILLS_DST)/"
	@$(SKILLS_LINK)
	@printf "$(GREEN)deployed$(NC) skills to $(SKILLS_DST)\n"

# Internal scan behind skills-status (mode "all": MISSING or DIFFERS -> exit 1, full OK/DIFFERS/MISSING
# report + Codex link check) and the skills-personal-repo-to-live gate (mode "drift": DIFFERS only -> exit 1;
# MISSING is fine, i.e. never deployed yet).
_skills-scan:
	@rc=0; \
	[ "$$SKILLS_SCAN_MODE" = "all" ] && printf "$(CYAN)== $(SKILLS_SRC) -> $(SKILLS_DST)$(NC)\n"; \
	for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		if [ ! -e "$(SKILLS_DST)/$$name" ]; then \
			[ "$$SKILLS_SCAN_MODE" = "all" ] && { printf "  $(YELLOW)MISSING$(NC)  $$name\n"; rc=1; }; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" >/dev/null 2>&1; then \
			printf "  $(RED)DIFFERS$(NC)  $$name  ($$($(SKILLS_NEWER) "$$d" "$(SKILLS_DST)/$$name" "$(GREEN)" "$(YELLOW)" "$(NC)"))\n"; diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" | sed 's/^/           /'; rc=1; \
		elif [ "$$SKILLS_SCAN_MODE" = "all" ]; then printf "  $(GREEN)OK$(NC)       $$name\n"; fi; \
	done; \
	if [ "$$SKILLS_SCAN_MODE" = "drift" ]; then \
		if [ $$rc -ne 0 ]; then printf "$(RED)drift check: DRIFT found$(NC) (live differs from git; see DIFFERS above)\n"; \
		else printf "$(GREEN)drift check: no drift$(NC) (live copies match git, or are not yet deployed)\n"; fi; \
	fi; \
	exit $$rc
	@if [ "$$SKILLS_SCAN_MODE" = all ]; then $(SKILLS_LINK) --check; else $(SKILLS_LINK) --preflight; fi

skills-status: ## One read-only report: repo vs live copies, Codex links, Hermes name clashes, skills missing from skills.keep, third-party lock/content
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

skills-personal-live-to-repo: ## Save live personal skills into the repo: NAME=<name> for one, ALL=1 for every unlisted one
	@if [ -n "$(NAME)" ]; then names="$(NAME)"; \
	elif [ "$(ALL)" = "1" ]; then \
		names=$$(for d in "$(SKILLS_DST)"/*/; do \
			[ -d "$$d" ] || continue; n=$$(basename "$$d"); \
			grep -v '^[[:space:]]*#' $(SKILLS_KEEP) 2>/dev/null | grep -qxF "$$n" && continue; \
			grep -qE "^[[:space:]]+\"$$n\": \{" $(THIRD_PARTY_LOCK) 2>/dev/null && continue; \
			echo "$$n"; \
		done); \
		[ -n "$$names" ] || { printf "$(YELLOW)skills-personal-live-to-repo:$(NC) no unlisted live skill to capture\n"; exit 0; }; \
	else printf "$(RED)usage:$(NC) make skills-personal-live-to-repo NAME=<name> | ALL=1\n"; exit 1; fi; \
	for NAME in $$names; do \
		[ -d "$(SKILLS_DST)/$$NAME" ] || { printf "$(RED)skip$(NC) %s: not live at %s\n" "$$NAME" "$(SKILLS_DST)/$$NAME"; continue; }; \
		mkdir -p "$(SKILLS_SRC)/$$NAME"; \
		cp -R "$(SKILLS_DST)/$$NAME/." "$(SKILLS_SRC)/$$NAME/"; \
		touch $(SKILLS_KEEP); \
		grep -qxF "$$NAME" $(SKILLS_KEEP) || echo "$$NAME" >> $(SKILLS_KEEP); \
		printf "$(GREEN)kept$(NC) %s\n" "$$NAME"; \
	done

# ── Aggregate: both classes, both directions ──────────────────────────────────────────────────
skills-all-repo-to-live: ## Deploy EVERYTHING out: personal tree + third-party replay + Codex links, then verify
	@rc=0; \
	$(MAKE) --no-print-directory skills-personal-repo-to-live || rc=1; \
	$(MAKE) --no-print-directory skills-link || rc=1; \
	$(MAKE) --no-print-directory skills-thirdparty-repo-to-live || { printf "$(YELLOW)third-party replay failed$(NC) -- needs npx + jq + a reachable lock\n"; rc=1; }; \
	$(MAKE) --no-print-directory skills-check || rc=1; \
	$(MAKE) --no-print-directory skills-status || rc=1; \
	exit $$rc

skills-all-live-to-repo: ## Capture EVERYTHING back: unlisted live skills + the npx lock, then verify
	@rc=0; \
	$(MAKE) --no-print-directory skills-personal-live-to-repo ALL=1 || rc=1; \
	if [ -f "$(LIVE_SKILLS_LOCK)" ]; then \
		$(MAKE) --no-print-directory skills-thirdparty-live-to-repo || rc=1; \
	else printf "$(YELLOW)skills-all-live-to-repo:$(NC) no live npx lock -- third-party capture skipped\n"; fi; \
	$(MAKE) --no-print-directory skills-status || rc=1; \
	exit $$rc

# ── Third-party skills (npx skills) ────────────────────────────────────────────────────────────
# `npx skills` is the mechanism for third-party SKILLS-ONLY packs. Its lock lives OUTSIDE any repo
# (a global install: $(XDG_STATE_HOME)/skills/.skill-lock.json on current CLIs, $(HOME)/.agents/.skill-lock.json
# on older ones)
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
	@test -f "$(LIVE_SKILLS_LOCK)" || { printf '$(RED)no live lock$(NC) at %s\n' "$(LIVE_SKILLS_LOCK)"; exit 1; }
	@jq . "$(LIVE_SKILLS_LOCK)" > "$(THIRD_PARTY_LOCK)"  # jq also adds the trailing newline the end-of-file hook requires
	@printf '$(GREEN)recorded$(NC) %s -- %s entries\n' "$(THIRD_PARTY_LOCK)" "$$(jq -r '$(JQ_TP_NAMES)' $(THIRD_PARTY_LOCK) | wc -l | tr -d ' ')"

# The replay logic lives in ONE script shared with chezmoi (run_after_ in the same dir).
THIRD_PARTY_REPLAY := src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh

skills-thirdparty-repo-to-live: ## Install and verify third-party skills for AGENTS (default Claude + Codex)
	@AGENTS="$(TARGET_AGENTS)" LOCK="$(abspath $(THIRD_PARTY_LOCK))" SKILLS_DST="$(SKILLS_DST)" SKILLS_CODEX_DST="$(SKILLS_CODEX_DST)" SKILLS_PYTHON="$(SKILLS_PYTHON)" LIVE_SKILLS_LOCK="$(LIVE_SKILLS_LOCK)" SKILLS_RECEIPTS="$(SKILLS_RECEIPTS)" FORCE=1 STRICT=1 bash $(THIRD_PARTY_REPLAY)
