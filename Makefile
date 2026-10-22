# Wire this repo into a skills directory, and keep it inside its budgets.
#
# The repo is the single source of truth: each image-* directory is symlinked
# individually into every installed CLI's skills directory (claude, codex,
# agy), so each of those directories keeps whatever else it already carries.

REPO       := $(CURDIR)
CLAUDE_DIR ?= $(HOME)/.claude/skills
CODEX_DIR  ?= $(HOME)/.codex/skills
AGY_DIR    ?= $(HOME)/.gemini/antigravity-cli/skills

# Every CLI reading a SKILL.md gets the same working tree. A host is only
# written to when it is installed here, and its own home — the parent of the
# skills directory — is what says so: judging by the skills directory itself
# would skip a host that has one but has never been given a skill.
HOST_DIRS  := $(CLAUDE_DIR) $(CODEX_DIR) $(AGY_DIR)

.DEFAULT_GOAL := help
.PHONY: help check validate test figures figures-test tools-test engines refute render hooks link unlink status

help:
	@echo "make check        validate + test + figures + figures-test + tools-test (what CI runs)"
	@echo "make validate     static rules over the corpus"
	@echo "make test         prove every rule still fires"
	@echo "make figures      recompute the numbers the reference layer states"
	@echo "make figures-test prove every figure check still fires"
	@echo "make tools-test   prove imgfacts and recipe read what is there"
	@echo "make refute CLAIMS=f.json RUNNING=claude   put each claim to the engines that did not make it"
	@echo "make engines  ask each checker engine for one object; reports what is unreachable"
	@echo "make render    write the delivered blocks back into every SKILL.md"
	@echo "make hooks     install the pre-commit hook"
	@echo "make link      symlink the skills into claude / codex / agy"
	@echo "make unlink    remove those symlinks"
	@echo "make status    show what is linked"

check: validate test figures figures-test tools-test

validate:
	@python3 image-tools/validate.py

test:
	@python3 image-tools/test_validate.py

figures:
	@python3 image-tools/figures_check.py

figures-test:
	@python3 image-tools/test_figures.py

tools-test:
	@python3 image-tools/test_tools.py

engines:
	@python3 image-tools/engine.py --selftest

refute:
	@# RUNNING is stated, never defaulted: a default would send work from codex
	@# or agy back to the engine that made it.
	@test -n "$(CLAIMS)" && test -n "$(RUNNING)" || { echo "usage: make refute CLAIMS=claims.json RUNNING=<claude|codex|agy>"; exit 2; }
	@python3 image-tools/refute.py --running "$(RUNNING)" "$(CLAIMS)"

render:
	@python3 image-tools/render.py

# Asked of git rather than assumed: in a worktree or a submodule `.git` is a
# file, and core.hooksPath may point somewhere else entirely.
# A different pre-commit already there (a team's, under a shared hooksPath) is
# left alone unless FORCE=1 says to replace it. An earlier version of this set's
# own hook is recognised by its first comment and upgraded.
hooks:
	@hooks=$$(git rev-parse --git-path hooks) && mkdir -p "$$hooks" && \
		if [ -e "$$hooks/pre-commit" ] && [ "$(FORCE)" != 1 ] \
			&& ! grep -q "Budgets enforced by a mechanism" "$$hooks/pre-commit"; then \
			echo "$$hooks/pre-commit exists and is not this set's; run: make hooks FORCE=1 to replace it"; exit 1; \
		fi && \
		cp image-tools/githooks/pre-commit "$$hooks/pre-commit" && \
		chmod +x "$$hooks/pre-commit" && echo "pre-commit installed in $$hooks"

# A skill is a directory holding a SKILL.md, under skills/ where the plugin
# format expects it. The prefix alone is not the test: image-registry/ and
# image-tools/ share it and must never be installed.
SKILL_DIRS := $(patsubst %/SKILL.md,%,$(wildcard skills/image-*/SKILL.md))
SKILL_NAMES := $(notdir $(SKILL_DIRS))

# A skill renamed or retired here leaves its link behind in every host, pointing
# into this checkout at a directory that is gone. Looping over today's skills
# alone never sees it, so unlink and status also look for links into this repo's
# skills/ under a name this repo no longer has.
RETIRED = for target in "$$dir"/image-*; do \
		[ -L "$$target" ] || continue; name=$$(basename "$$target"); \
		case " $(SKILL_NAMES) " in *" $$name "*) continue;; esac; \
		case "$$(readlink "$$target")" in "$(REPO)/skills/"*) ;; *) continue;; esac; \
		$(1); \
	done

link:
	@for dir in $(HOST_DIRS); do \
		if [ ! -d "$$(dirname "$$dir")" ]; then echo "skip $$dir (host not installed here)"; continue; fi; \
		mkdir -p "$$dir"; \
		echo "$$dir"; \
		for path in $(SKILL_DIRS); do \
			name=$$(basename "$$path"); target="$$dir/$$name"; \
			if [ -e "$$target" ] && [ ! -L "$$target" ]; then \
				echo "  skip $$name (a real path is already there)"; \
			elif [ -L "$$target" ] && [ ! -e "$$target" ] \
				&& case "$$(readlink "$$target")" in */skills/$$name) true;; *) false;; esac; then \
				old=$$(readlink "$$target"); ln -sfn "$(REPO)/$$path" "$$target"; \
				echo "  link $$name (replaced a dangling link to an old checkout, $$old)"; \
			elif [ -L "$$target" ] && [ "$$(readlink "$$target")" != "$(REPO)/$$path" ]; then \
				echo "  skip $$name (links to $$(readlink "$$target"), not here)"; \
			else \
				ln -sfn "$(REPO)/$$path" "$$target"; echo "  link $$name"; \
			fi; \
		done; \
	done

unlink:
	@for dir in $(HOST_DIRS); do \
		[ -d "$$dir" ] || continue; \
		echo "$$dir"; \
		for path in $(SKILL_DIRS); do \
			name=$$(basename "$$path"); target="$$dir/$$name"; \
			if [ -L "$$target" ] && [ "$$(readlink "$$target")" = "$(REPO)/$$path" ]; then \
				rm "$$target"; echo "  unlink $$name"; \
			elif [ -L "$$target" ]; then echo "  skip $$name (not this repo's link)"; fi; \
		done; \
		$(call RETIRED,rm "$$target" && echo "  unlink $$name (no longer a skill here)"); \
	done

status:
	@for dir in $(HOST_DIRS); do \
		echo "$$dir"; \
		for path in $(SKILL_DIRS); do \
			name=$$(basename "$$path"); target="$$dir/$$name"; \
			if [ -L "$$target" ] && [ "$$(readlink "$$target")" = "$(REPO)/$$path" ]; then \
				if [ -e "$$target" ]; then echo "  linked   $$name"; \
				else echo "  dangling $$name"; fi; \
			elif [ -L "$$target" ] && [ ! -e "$$target" ]; then echo "  dangling $$name -> $$(readlink "$$target")"; \
			elif [ -e "$$target" ] || [ -L "$$target" ]; then echo "  foreign  $$name"; \
			else echo "  unlinked $$name"; fi; \
		done; \
		$(call RETIRED,echo "  retired  $$name -> $$(readlink "$$target")  (make unlink removes it)"); \
	done
