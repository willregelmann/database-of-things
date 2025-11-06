# Curator System

Agentic curator system for managing collectible database collections.

## Features

- 🤖 **Conversational Discovery** - Design curators through interactive sessions
- 📜 **Script Generation** - Auto-generate domain-specific data fetching scripts
- 🔄 **Autonomous Execution** - Scheduled runs with agent-driven decision making
- 🛠️ **Generic Tools** - Collection management tools work for any domain
- 🔐 **Secrets Management** - Secure API key storage per curator
- 📊 **Transaction Log** - Rollback/resume capability for all operations

## Quick Start

```bash
# Install
cd curator
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials

# Initialize a curator
curator init "Pokemon TCG"

# Run manually
curator run "Pokemon TCG"

# Schedule automatic runs
curator schedule "Pokemon TCG" "0 2 * * *"  # Daily at 2 AM

# View status
curator status "Pokemon TCG"
```

## Architecture

See `docs/plans/2025-11-06-curator-system.md` for implementation details.
