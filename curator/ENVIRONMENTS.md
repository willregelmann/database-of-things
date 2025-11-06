# Environment Configuration

The curator system supports multiple environments (local, staging, production) using environment-specific `.env` files.

## Quick Setup

### 1. Local Development (Default)

```bash
# Copy the example file
cp .env.local.example .env.local

# Edit with your local Supabase credentials
# SUPABASE_URL=http://127.0.0.1:54321
# SUPABASE_SERVICE_KEY=sb_secret_...
```

Run local Supabase:
```bash
./bin/supabase start
```

Get your service key:
```bash
./bin/supabase status | grep "service_role key"
```

### 2. Production Setup

```bash
# Copy the example file
cp .env.production.example .env.production

# Edit with your production Supabase credentials
# SUPABASE_URL=https://yourproject.supabase.co
# SUPABASE_SERVICE_KEY=eyJhbGci...
```

Get production credentials from Supabase Dashboard:
- Project Settings → API → Service Role key

### 3. Staging (Optional)

```bash
cp .env.staging.example .env.staging
# Edit with staging credentials
```

---

## Using Environments

### Default Behavior (No --env flag)
Uses `.env.local` if it exists, otherwise `.env`:

```bash
curator init "Pokemon TCG"
curator run "Pokemon TCG"
curator status "Pokemon TCG"
```

### Explicit Environment Selection

```bash
# Use production
curator --env production init "Pokemon TCG"
curator --env production run "Pokemon TCG"
curator --env production status "Pokemon TCG"

# Use staging
curator --env staging run "Pokemon TCG"

# Use local explicitly
curator --env local status "Pokemon TCG"
```

---

## File Priority

1. `--env` flag specified → Use `.env.{env}`
2. No flag → Try `.env.local` first
3. Fallback → Use `.env`

---

## Security Best Practices

✅ **DO:**
- Keep `.env.*` files in `.gitignore` (already configured)
- Use service role keys only in secure environments
- Rotate keys regularly
- Use different Anthropic API keys per environment if needed

❌ **DON'T:**
- Commit `.env` files to git
- Share service role keys in public channels
- Use production keys in local development

---

## Migration to Production

Before running curators in production, ensure the database has the required tables:

```bash
# Apply migrations to production
./bin/supabase db push --linked

# Or manually apply:
# 1. Link to production: ./bin/supabase link
# 2. Push migrations: ./bin/supabase db push
```

Alternatively, run migrations from the SQL files in `supabase/migrations/` directly in Supabase Dashboard.

---

## Troubleshooting

**Error: Environment file not found**
```
Error: Environment file not found: curator/.env.production
```
→ Create the file: `cp .env.production.example .env.production`

**Wrong database being accessed**
```
# Check which environment is loaded
curator --env production status "Pokemon TCG"
# Should show: "Loaded environment: production"
```

**Credentials not working**
```
# Verify credentials
curl https://yourproject.supabase.co/rest/v1/ \
  -H "apikey: YOUR_SERVICE_KEY"
```
