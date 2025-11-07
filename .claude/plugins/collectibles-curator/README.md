# Collectibles Curator Plugin

Autonomous agents that import items into collectibles databases.

## Usage

### Initialize a Curator

```bash
/curator:init "Pokemon TCG"
```

Interactive discovery session that generates import plan and scripts.

### Run a Curator

```bash
/curator:run "Pokemon TCG"
```

Autonomously executes the import plan, debugging and fixing issues.

### Check Status

```bash
/curator:status "Pokemon TCG"
```

Shows collection stats and curator details.

## How It Works

1. **Discovery** - Socratic questioning to understand collection and data sources
2. **Generation** - Creates `plan.md` and Python scripts in `.curator/curators/{name}/`
3. **Execution** - Runs scripts autonomously, fixing errors and installing dependencies
4. **Reporting** - Summarizes imported items and issues resolved

## Directory Structure

```
.curator/
  curators/
    Pokemon TCG/
      plan.md           # Import strategy
      config.json       # Collection ID, settings
      scripts/
        fetch_data.py   # Fetch from API/website
        import_items.py # Import into database
        validate.py     # Optional validation
      secrets.env       # API keys (gitignored)
```
