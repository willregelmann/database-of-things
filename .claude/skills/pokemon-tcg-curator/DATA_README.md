# Pokemon TCG Local Data

This directory contains a clone of the [pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data) repository.

## What is this?

The pokemon-tcg-data repository contains **all Pokemon TCG sets and cards in JSON format**. This provides a fast, offline alternative to the Pokemon TCG API.

## Structure

```
data/
├── sets/
│   └── en.json          # All English sets
├── cards/
│   └── en/
│       ├── base1.json   # Base Set cards
│       ├── swsh4.json   # Vivid Voltage cards
│       └── ...          # All other sets
```

## Usage

The `import_from_data.py` script reads these JSON files directly:

```bash
# Import all sets and cards
../venv/bin/python3 import_from_data.py

# Import specific set
../venv/bin/python3 import_from_data.py --set base1
```

## Updating

To get the latest data:

```bash
cd data
git pull
```

The data is regularly updated by the Pokemon TCG community.

## Why use local data?

- **Fast**: No API calls, no rate limits
- **Offline**: Works without internet
- **Reliable**: No API timeouts or downtime
- **Complete**: All sets and cards in one place

## Credit

Data maintained by: https://github.com/PokemonTCG/pokemon-tcg-data
