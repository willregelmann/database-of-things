import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { readdir, readFile, access } from "fs/promises";
import { join } from "path";

const CURATOR_BASE_PATH = join(process.cwd(), ".curator/specs");

interface CuratorMeta {
  name: string;
  type: "agent" | "script";
  collection_name?: string;
}

async function listCuratorMeta(): Promise<CuratorMeta[]> {
  try {
    const dirs = await readdir(CURATOR_BASE_PATH, { withFileTypes: true });
    const results: CuratorMeta[] = [];

    for (const dir of dirs) {
      if (!dir.isDirectory()) continue;
      const curatorPath = join(CURATOR_BASE_PATH, dir.name);
      let type: "agent" | "script" = "script";
      let collection_name: string | undefined;

      try {
        const config = JSON.parse(await readFile(join(curatorPath, "config.json"), "utf-8"));
        type = config.type === "agent" ? "agent" : "script";
        collection_name = config.collection_name;
      } catch {
        // No config.json — check for scripts/fetch_data.py to determine type
        const hasScript = await access(join(curatorPath, "scripts", "fetch_data.py")).then(() => true).catch(() => false);
        type = hasScript ? "script" : "agent";
      }

      results.push({ name: dir.name, type, collection_name });
    }
    return results;
  } catch {
    return [];
  }
}

async function readCuratorSpec(name: string): Promise<string> {
  const curatorPath = join(CURATOR_BASE_PATH, name);

  let config: Record<string, any> = {};
  try {
    config = JSON.parse(await readFile(join(curatorPath, "config.json"), "utf-8"));
  } catch { /* no config */ }

  let promptContent: string | null = null;
  try {
    promptContent = await readFile(join(curatorPath, "prompt.md"), "utf-8");
  } catch { /* no prompt.md */ }

  // Collect collection IDs
  const collectionIds: Record<string, string> = {};
  for (const suffix of ["local", "prod"]) {
    try {
      const secrets = await readFile(join(curatorPath, `secrets.${suffix}.env`), "utf-8");
      const match = secrets.match(/COLLECTION_ID=([^\s]+)/);
      if (match) collectionIds[suffix] = match[1];
    } catch { /* no secrets file */ }
  }

  return JSON.stringify({ name, config, prompt: promptContent, collection_ids: collectionIds }, null, 2);
}

export function register(server: McpServer) {
  const template = new ResourceTemplate("curator://{name}", {
    list: async () => {
      const curators = await listCuratorMeta();
      return {
        resources: curators.map(c => ({
          uri: `curator://${encodeURIComponent(c.name)}`,
          name: c.name,
          description: `${c.type} curator${c.collection_name ? ` for ${c.collection_name}` : ""}`,
          mimeType: "application/json",
        })),
      };
    },
  });

  server.resource(
    "curator",
    template,
    { title: "Curator specification", description: "Config, prompt, and collection IDs for a curator", mimeType: "application/json" },
    async (uri, { name }) => {
      const curatorName = decodeURIComponent(name as string);
      const spec = await readCuratorSpec(curatorName);
      return { contents: [{ uri: uri.href, text: spec, mimeType: "application/json" }] };
    }
  );
}
