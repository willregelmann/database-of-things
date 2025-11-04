#!/usr/bin/env node

/**
 * Auto-detect Supabase credentials from CLI or .env
 *
 * Priority:
 * 1. Supabase CLI (if linked project exists)
 * 2. .env file
 * 3. Exit with error
 */

import { execSync } from 'child_process';
import { config } from 'dotenv';
import { existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Try to get credentials from Supabase CLI
 */
function getCredentialsFromCLI() {
  try {
    // Get linked project
    const projectsOutput = execSync('supabase projects list', { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] });

    // Parse the linked project reference ID
    const linkedLine = projectsOutput.split('\n').find(line => line.trim().startsWith('●'));
    if (!linkedLine) {
      return null;
    }

    // Extract project reference (3rd column)
    const parts = linkedLine.split('|').map(p => p.trim());
    const projectRef = parts[2];

    if (!projectRef) {
      return null;
    }

    // Get API keys for the project
    const apiKeysOutput = execSync(`supabase projects api-keys --project-ref ${projectRef}`, {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'ignore']
    });

    // Parse service_role key
    const serviceRoleLine = apiKeysOutput.split('\n').find(line => line.includes('service_role'));
    if (!serviceRoleLine) {
      return null;
    }

    const keyParts = serviceRoleLine.split('|').map(p => p.trim());
    const serviceRoleKey = keyParts[1];

    if (!serviceRoleKey) {
      return null;
    }

    // Build Supabase URL
    const supabaseUrl = `https://${projectRef}.supabase.co`;

    return {
      SUPABASE_URL: supabaseUrl,
      SUPABASE_SERVICE_KEY: serviceRoleKey,
      source: 'cli'
    };
  } catch (error) {
    return null;
  }
}

/**
 * Try to get credentials from .env file
 */
function getCredentialsFromEnv() {
  const envPath = join(__dirname, '.env');

  if (!existsSync(envPath)) {
    return null;
  }

  config({ path: envPath });

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;

  if (!url || !key) {
    return null;
  }

  return {
    SUPABASE_URL: url,
    SUPABASE_SERVICE_KEY: key,
    source: 'env'
  };
}

/**
 * Get credentials from any available source
 */
export function getCredentials() {
  // Try CLI first
  const cliCreds = getCredentialsFromCLI();
  if (cliCreds) {
    return cliCreds;
  }

  // Fall back to .env
  const envCreds = getCredentialsFromEnv();
  if (envCreds) {
    return envCreds;
  }

  return null;
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
  const creds = getCredentials();

  if (!creds) {
    console.error('❌ Could not find Supabase credentials');
    console.error('\nTried:');
    console.error('  1. Supabase CLI (no linked project found)');
    console.error('  2. .env file (not found or incomplete)');
    console.error('\nSolutions:');
    console.error('  A. Link to Supabase project: supabase link');
    console.error('  B. Create .env file with SUPABASE_URL and SUPABASE_SERVICE_KEY');
    process.exit(1);
  }

  console.log(`✅ Found credentials from: ${creds.source}`);
  console.log(`   URL: ${creds.SUPABASE_URL}`);
  console.log(`   Key: ${creds.SUPABASE_SERVICE_KEY.substring(0, 20)}...`);
}
