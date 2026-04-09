import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdir, readFile } from "fs/promises";
import { join } from "path";

const CURATOR_BASE_PATH = join(process.cwd(), ".curator/specs");

async function findCurator(name: string): Promise<string> {
  const dirs = await readdir(CURATOR_BASE_PATH, { withFileTypes: true });
  const names = dirs.filter(d => d.isDirectory()).map(d => d.name);

  // Exact match first
  const exact = names.find(n => n.toLowerCase() === name.toLowerCase());
  if (exact) return exact;

  // Prefix/contains match
  const fuzzy = names.find(n => n.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(n.toLowerCase()));
  if (fuzzy) return fuzzy;

  throw new Error(`No curator found matching "${name}". Available: ${names.join(", ")}`);
}

async function buildExecutionPrompt(name: string, env: string, extraInstructions?: string): Promise<string> {
  const curatorPath = join(CURATOR_BASE_PATH, name);

  let config: Record<string, any> = {};
  try {
    config = JSON.parse(await readFile(join(curatorPath, "config.json"), "utf-8"));
  } catch { /* no config */ }

  const curatorType = config.type ?? (await readFile(join(curatorPath, "scripts/fetch_data.py"), "utf-8").then(() => "script").catch(() => "agent"));

  let collectionId = "";
  try {
    const secrets = await readFile(join(curatorPath, `secrets.${env}.env`), "utf-8");
    const match = secrets.match(/COLLECTION_ID=([^\s]+)/);
    if (match) collectionId = match[1];
  } catch { /* no secrets */ }

  if (curatorType === "script") {
    return `You are running the **${name}** script-based curator in **${env}** mode.

This curator uses a Python fetch script to pull data from an external API. Run it via:

\`\`\`bash
.venv/bin/python -m curator run "${name}" --env=${env}${extraInstructions ? ` # Note: ${extraInstructions}` : ""}
\`\`\`

The pipeline is resumable — re-running skips already-completed phases (tracked in \`.curator/specs/${name}/run_status.json\`). Delete \`run_status.json\` to force a full re-run.

If the run fails, read the error, check \`.curator/specs/${name}/scripts/fetch_data.py\`, fix the issue, and re-run.`;
  }

  // Agent curator — read prompt.md
  let promptMd = "";
  try {
    promptMd = await readFile(join(curatorPath, "prompt.md"), "utf-8");
  } catch {
    throw new Error(`Curator "${name}" has no prompt.md. Cannot run as agent curator.`);
  }

  return `You are executing the **${name}** agent curator for the database-of-things project.

## Collection Target
- **Environment**: ${env}
- **Collection ID**: ${collectionId || "(not configured — check secrets.${env}.env)"}

## Curator Specification

${promptMd}

## Config
${JSON.stringify(config, null, 2)}

## Execution Protocol

1. **Research** — Follow the spec above to find items. Honor any scope constraints.
2. **Sample review** — Before importing, show the user 5 representative items and the total count. Wait for approval.
3. **Import** — Use the \`entities_upsert\` MCP tool:
   - \`collection_id\`: \`${collectionId}\`
   - \`items\`: array of items following the schema in the spec
   - \`skip_duplicates\`: true
   - \`localize_images\`: true
4. **Report** — Summarize: created / updated / skipped counts and any errors.

## Guidelines
- Make judgment calls about scope rather than asking for every edge case
- Log decisions in \`.curator/specs/${name}/research_notes.md\` for future reference
- Missing images or minor data gaps should not block the import
${extraInstructions ? `\n## Additional Instructions\n${extraInstructions}` : ""}`;
}

export function register(server: McpServer) {
  server.prompt(
    "run_curator",
    "Generate execution instructions for a curator import. Injects the curator's spec and collection ID into a ready-to-execute protocol.",
    {
      name: z.string().describe("Curator name (fuzzy matched against available curators)"),
      env: z.enum(["local", "prod"]).default("local").describe("Target environment"),
      instructions: z.string().optional().describe("Optional additional instructions (e.g. '--limit 50', 'only fetch new sets')"),
    },
    async ({ name, env, instructions }) => {
      const curatorName = await findCurator(name);
      const text = await buildExecutionPrompt(curatorName, env, instructions);
      return {
        messages: [{
          role: "user",
          content: { type: "text", text },
        }],
      };
    }
  );
}
