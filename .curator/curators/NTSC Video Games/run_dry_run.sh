#!/bin/bash
export SUPABASE_URL=http://127.0.0.1:54321
export SUPABASE_SERVICE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz
export COLLECTION_ID=placeholder
export PLATFORM_ID=18

cd "$(dirname "$0")"
python3 scripts/import_items.py --dry-run
