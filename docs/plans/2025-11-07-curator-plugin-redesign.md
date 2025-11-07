# Curator System: Claude Code Plugin Redesign

**Date:** 2025-11-07
**Status:** Design Complete

## Overview

The curator system manages autonomous agents that import items into collectibles databases. The current implementation uses a custom Claude API runner with limited tools. This design replaces it with a Claude Code plugin, giving curators full debugging and iteration capabilities.

## Problem

The current curator system has two critical flaws:

1. **Limited agency** - Curators execute pre-written scripts but cannot fix broken code, install dependencies, or adapt to API changes
2. **Excessive explicitness** - The discovery prompt and runner require detailed instructions to make curators perform basic import tasks

Users trust Claude Code because it debugs, iterates, and succeeds autonomously. Curators should work the same way.

## Solution

Build a Claude Code plugin with two skills:

1. **init-curator** - Interactive discovery session that generates import plans and scripts
2. **run-curator** - Autonomous execution that makes the import succeed

Users invoke these through slash commands: `/curator:init "Pokemon TCG"` and `/curator:run "Pokemon TCG"`.

## Architecture

### Plugin Structure

```
.claude/
  commands/
    curator-init.md          # /curator:init command
    curator-run.md           # /curator:run command
    curator-status.md        # /curator:status command

  plugins/
    collectibles-curator/
      skills/
        init-curator/
          SKILL.md           # Discovery session skill
        run-curator/
          SKILL.md           # Execution skill

.curator/                    # Curator artifacts (not in plugin)
  curators/
    Pokemon TCG/
      plan.md                # Import strategy
      config.json            # Collection ID, settings
      scripts/
        fetch_data.py        # Fetch items from API/website
        import_items.py      # Import into database
        validate.py          # Optional validation
      secrets.env            # API keys (gitignored)
```

### Discovery Workflow

User runs `/curator:init "Pokemon TCG"`.

Claude Code (through the init-curator skill):
1. Asks questions one at a time (Socratic method, like brainstorming skill)
2. Learns about the collection, data sources, and deduplication strategy
3. Creates artifacts in `.curator/curators/Pokemon TCG/`:
   - `plan.md` - Import workflow and strategy
   - `config.json` - Collection ID and settings
   - `scripts/` - Complete, working Python scripts
4. Commits the curator to git

Questions focus on **data import**: Where does data come from? How do we fetch it? What makes items unique?

### Execution Workflow

User runs `/curator:run "Pokemon TCG"`.

Claude Code (through the run-curator skill):
1. Loads the plan from `.curator/curators/Pokemon TCG/plan.md`
2. Loads secrets from `secrets.env` (if exists)
3. Executes the import workflow:
   - Runs `python scripts/fetch_data.py`
   - If it fails: debugs the script, installs dependencies, retries
   - Runs `python scripts/import_items.py`
   - If it fails: debugs, fixes, retries
4. Reports results (items imported, issues fixed)

The skill emphasizes **autonomous success**: fix broken scripts, adapt to API changes, install dependencies, iterate until import succeeds.

### Status Command

User runs `/curator:status "Pokemon TCG"`.

Displays:
- Collection stats (total items, last updated)
- Plan summary
- Recent activity (if tracked)

## Implementation

### Skill 1: init-curator

```markdown
# .claude/plugins/collectibles-curator/skills/init-curator/SKILL.md

---
name: init-curator
description: Initialize a new curator through interactive discovery
---

You are designing a curator agent for a collectibles database.

**Process:**

1. **Ask questions** (one at a time, like brainstorming):
   - What items belong in this collection?
   - Where does data come from? (APIs, websites to scrape)
   - What makes items unique? (deduplication key)
   - How should items be organized?

2. **Create artifacts** in `.curator/curators/{name}/`:
   - `plan.md` - Import strategy, data sources, workflow
   - `config.json` - Collection ID, settings
   - `scripts/fetch_data.py` - Fetch items from source
   - `scripts/import_items.py` - Import into database
   - `scripts/validate.py` - Optional validation

3. **Generate working scripts**:
   - Complete, executable Python code
   - Handle errors, install dependencies
   - Focus on DATA IMPORT (scraping → importing)

4. **Commit the curator**:
   - Git commit: "Add {name} curator"

Ask questions one at a time. Generate complete working code.
```

### Skill 2: run-curator

```markdown
# .claude/plugins/collectibles-curator/skills/run-curator/SKILL.md

---
name: run-curator
description: Execute a curator plan autonomously
---

You execute curator plans to import items into collections.

**Your task:**

1. **Load the plan** from `.curator/curators/{name}/plan.md`
2. **Load secrets** from `secrets.env` (if exists)
3. **Execute the import workflow**:
   - Run: `python scripts/fetch_data.py`
   - If it fails: debug, fix script, install dependencies, retry
   - Run: `python scripts/import_items.py`
   - If it fails: debug, fix, retry
   - Run validation (optional)

4. **Be autonomous**:
   - Fix broken scripts (parsing errors, API changes)
   - Install missing dependencies (`pip install`)
   - Adapt to API/website structure changes
   - Iterate until successful

5. **Report results**:
   - Items imported
   - Issues encountered and fixed
   - Collection stats

You have full access to Read, Write, Bash, WebFetch.
Your job is to make the import succeed.
```

### Slash Commands

```markdown
# .claude/commands/curator-init.md
---
name: /curator:init
description: Initialize a new curator
---

Usage: /curator:init "Collection Name" [--collection-id UUID]

Launches init-curator skill for interactive discovery.
```

```markdown
# .claude/commands/curator-run.md
---
name: /curator:run
description: Execute a curator plan
---

Usage: /curator:run "Collection Name"

Launches run-curator skill to import items autonomously.
```

```markdown
# .claude/commands/curator-status.md
---
name: /curator:status
description: Show curator statistics
---

Usage: /curator:status "Collection Name"

Displays collection stats, plan summary, recent activity.
```

## User Experience

```bash
# Initialize new curator
$ /curator:init "Pokemon TCG"
# → Interactive questions about collection
# → Creates .curator/curators/Pokemon TCG/

# Execute curator
$ /curator:run "Pokemon TCG"
# → Loads plan
# → Runs fetch and import scripts
# → Debugs and fixes issues autonomously
# → Reports: "Imported 152 cards from pokemontcg.io"

# Check status
$ /curator:status "Pokemon TCG"
# → Collection: 152 cards, last updated 2 hours ago
```

## Migration Path

Current Python-based curator system becomes obsolete. Users create new curators through the plugin.

Existing curators in `.curator/curators/` can run through `/curator:run` if their directory structure matches (plan.md, scripts/, config.json).

## Benefits

1. **Full Claude Code capabilities** - Debug, iterate, install dependencies, adapt to changes
2. **Simpler architecture** - No custom runner, no Agent SDK complexity
3. **Free execution** - Uses existing Claude Code subscription
4. **Familiar patterns** - Discovery works like `/superpowers:brainstorm`
5. **Battle-tested reliability** - Claude Code has proven autonomous success

## Trade-offs

- **No scheduled execution** - Curators run manually, not on cron schedules
- **Interactive sessions** - Cannot run headless without user present
- **Session-based** - No persistent agent monitoring collections

These limitations are acceptable. Curators run on-demand when users need them, not as background daemons.

## Success Criteria

1. Users initialize curators through natural conversation
2. Generated scripts work on first execution or Claude Code fixes them
3. Curators successfully import items without user intervention
4. Users trust curators to debug and iterate autonomously

## Next Steps

1. Create plugin directory structure
2. Write init-curator and run-curator skills
3. Write slash command definitions
4. Test with Pokemon TCG curator
5. Document plugin in README
