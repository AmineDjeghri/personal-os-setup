# Agent skills symlink targets.
# Canonical skills live in .claude/skills; .agents/skills holds git symlinks so
# non-Claude agents (Hermes, Codex, OpenCode, skills CLI) see the same files.

.PHONY: skills-link skills-check skills-deploy skills-diff skills-drift skills-status skills-thirdparty skills-thirdparty-save skills-thirdparty-replay

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

skills-deploy: ## Copy shared skills to ~/.claude/skills and Hermes-only skills to ~/.hermes/skills (refuses if a live copy DIFFERS from git; SKILLS_FORCE=1 overrides)
ifeq ($(SKILLS_FORCE),1)
	@echo "skills-deploy: drift check SKIPPED (SKILLS_FORCE=1)"
else
	@$(MAKE) --no-print-directory skills-drift || { echo; echo "skills-deploy: ABORTED -- the live copies above differ from git."; echo "Reconcile the live version into git first, or re-run with SKILLS_FORCE=1 to overwrite them."; exit 1; }
endif
	@mkdir -p $(SKILLS_DST)
	@cp -R $(SKILLS_SRC)/. $(SKILLS_DST)/
	@echo "deployed shared skills to $(SKILLS_DST)"
	@mkdir -p $(HERMES_SKILLS_DST)
	@cp -R $(HERMES_SKILLS_SRC)/. $(HERMES_SKILLS_DST)/
	@echo "deployed Hermes-only skills to $(HERMES_SKILLS_DST)"

# skills-diff mode "all": MISSING or DIFFERS -> exit 1 (full OK/DIFFERS/MISSING report)
# skills-drift mode "drift": DIFFERS only -> exit 1; MISSING is fine (i.e. never deployed yet)
skills-diff: export SKILLS_SCAN_MODE = all
skills-drift: export SKILLS_SCAN_MODE = drift
skills-diff: ## Compare each git-managed skill against its live copy (read-only; exit 1 on MISSING or DIFFERS)
skills-drift: ## Like skills-diff but only fails on DIFFERS, not MISSING; the skills-deploy gate
skills-diff skills-drift:
	@rc=0; \
	[ "$$SKILLS_SCAN_MODE" = "all" ] && echo "== shared: $(SKILLS_SRC) -> $(SKILLS_DST)"; \
	for d in $(SKILLS_SRC)/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); \
		if [ ! -e "$(SKILLS_DST)/$$name" ]; then \
			[ "$$SKILLS_SCAN_MODE" = "all" ] && { echo "  MISSING  $$name"; rc=1; }; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" >/dev/null 2>&1; then \
			echo "  DIFFERS  $$name"; diff -rq --exclude=.DS_Store "$$d" "$(SKILLS_DST)/$$name" | sed 's/^/           /'; rc=1; \
		elif [ "$$SKILLS_SCAN_MODE" = "all" ]; then echo "  OK       $$name"; fi; \
	done; \
	[ "$$SKILLS_SCAN_MODE" = "all" ] && echo "== hermes-only: $(HERMES_SKILLS_SRC) -> $(HERMES_SKILLS_DST)"; \
	for d in $(HERMES_SKILLS_SRC)/*/*/; do \
		[ -d "$$d" ] || continue; name=$$(basename "$$d"); cat=$$(basename "$$(dirname "$$d")"); \
		if [ ! -e "$(HERMES_SKILLS_DST)/$$cat/$$name" ]; then \
			[ "$$SKILLS_SCAN_MODE" = "all" ] && { echo "  MISSING  $$cat/$$name"; rc=1; }; \
		elif ! diff -rq --exclude=.DS_Store "$$d" "$(HERMES_SKILLS_DST)/$$cat/$$name" >/dev/null 2>&1; then \
			echo "  DIFFERS  $$cat/$$name"; diff -rq --exclude=.DS_Store "$$d" "$(HERMES_SKILLS_DST)/$$cat/$$name" | sed 's/^/           /'; rc=1; \
		elif [ "$$SKILLS_SCAN_MODE" = "all" ]; then echo "  OK       $$cat/$$name"; fi; \
	done; \
	if [ "$$SKILLS_SCAN_MODE" = "drift" ]; then \
		if [ $$rc -ne 0 ]; then echo "skills-drift: DRIFT found (live differs from git; see DIFFERS above)"; \
		else echo "skills-drift: no drift (live copies match git, or are not yet deployed)"; fi; \
	fi; \
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

# ── Third-party skills (npx skills) ────────────────────────────────────────────────────────────
# `npx skills` is the mechanism for third-party SKILLS-ONLY packs. Its lock lives OUTSIDE any repo
# (for a global install: $(HOME)/.agents/.skill-lock.json), so the committed COPY below is what
# makes a new machine rebuildable. The copy deliberately does NOT sit in the chezmoi source: a
# `chezmoi apply` must never overwrite the tool's live lock with a stale record.
#
# The jq paths below are the ONLY place the lock schema is expressed, so a schema bump is a
# one-line fix. v3 lock shape: .skills.<name> = { source, sourceType, sourceUrl, skillPath,
# skillFolderHash }. VALIDATE ON FIRST REAL INSTALL (`make skills-thirdparty-save`) — written from
# the documented v3 shape, not yet from a lock produced on this box.
THIRD_PARTY_LOCK := third-party-skills.lock.json
LIVE_SKILLS_LOCK := $(HOME)/.agents/.skill-lock.json
JQ_TP_NAMES := .skills | keys[]
JQ_TP_HASH  := (.skills[$$n].skillFolderHash // "-")
JQ_TP_SRC   := (.skills[$$n].source // .skills[$$n].sourceUrl // "?")

skills-thirdparty: ## Report drift between the committed third-party lock and the live one (read-only)
	@if [ ! -f "$(LIVE_SKILLS_LOCK)" ]; then \
		printf 'no live lock at %s -- no third-party pack installed on this machine\n' "$(LIVE_SKILLS_LOCK)"; exit 0; \
	fi; \
	if [ ! -f "$(THIRD_PARTY_LOCK)" ]; then \
		printf 'no committed lock (%s) -- record the live one with: make skills-thirdparty-save\n' "$(THIRD_PARTY_LOCK)"; exit 1; \
	fi; \
	rc=0; \
	for n in $$(jq -r '$(JQ_TP_NAMES)' $(THIRD_PARTY_LOCK)); do \
		want=$$(jq -r --arg n "$$n" '$(JQ_TP_HASH)' $(THIRD_PARTY_LOCK)); \
		src=$$(jq -r --arg n "$$n" '$(JQ_TP_SRC)' $(THIRD_PARTY_LOCK)); \
		have=$$(jq -r --arg n "$$n" '$(JQ_TP_HASH)' $(LIVE_SKILLS_LOCK) 2>/dev/null); \
		if [ -z "$$have" ] || [ "$$have" = "-" ]; then \
			printf '  MISSING  %s (%s) -- replay: make skills-thirdparty-replay\n' "$$n" "$$src"; rc=1; \
		elif [ "$$have" != "$$want" ]; then \
			printf '  CHANGED  %s (%s)\n           committed %s\n           live      %s\n' "$$n" "$$src" "$$want" "$$have"; rc=1; \
		else \
			printf '  OK       %s\n' "$$n"; \
		fi; \
	done; \
	for n in $$(jq -r '$(JQ_TP_NAMES)' $(LIVE_SKILLS_LOCK)); do \
		if ! jq -e --arg n "$$n" '.skills[$$n]' $(THIRD_PARTY_LOCK) >/dev/null 2>&1; then \
			printf '  EXTRA    %s -- installed here but absent from the committed lock; record it: make skills-thirdparty-save\n' "$$n"; rc=1; \
		fi; \
	done; \
	if [ $$rc -ne 0 ]; then echo "skills-thirdparty: DRIFT (see above)"; else echo "skills-thirdparty: no drift"; fi; \
	exit $$rc

skills-thirdparty-save: ## Copy the live npx lock into the repo (the record we ship)
	@test -f "$(LIVE_SKILLS_LOCK)" || { printf 'no live lock at %s\n' "$(LIVE_SKILLS_LOCK)"; exit 1; }
	@cp "$(LIVE_SKILLS_LOCK)" "$(THIRD_PARTY_LOCK)"
	@printf 'recorded %s -- %s entries\n' "$(THIRD_PARTY_LOCK)" "$$(jq -r '$(JQ_TP_NAMES)' $(THIRD_PARTY_LOCK) | wc -l | tr -d ' ')"

skills-thirdparty-replay: ## Re-install every pack in the committed lock, then re-check (the update path)
	@test -f "$(THIRD_PARTY_LOCK)" || { printf 'no committed lock at %s\n' "$(THIRD_PARTY_LOCK)"; exit 1; }
	@command -v npx >/dev/null || { echo "npx is not present (agent container only)"; exit 1; }
	@for n in $$(jq -r '$(JQ_TP_NAMES)' $(THIRD_PARTY_LOCK)); do \
		src=$$(jq -r --arg n "$$n" '$(JQ_TP_SRC)' $(THIRD_PARTY_LOCK)); \
		if [ -z "$$src" ] || [ "$$src" = "?" ]; then printf 'skip %s: no source recorded\n' "$$n"; continue; fi; \
		printf 're-add %s from %s\n' "$$n" "$$src"; \
		npx -y skills add "$$src" -s "$$n" -a claude-code -g -y; \
	done
	@$(MAKE) --no-print-directory skills-thirdparty
