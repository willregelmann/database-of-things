#!/bin/bash
export SUPABASE_URL=http://127.0.0.1:54321
export SUPABASE_SERVICE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz
export COLLECTION_ID=7d0877e1-24d2-4955-9c96-725e2365a9ee

cd "$(dirname "$0")"
python3 scripts/import_items.py
