import { readdir, readFile } from "fs/promises";
import { join } from "path";

const CURATOR_BASE_PATH = join(process.cwd(), ".curator/curators");

interface Curator {
  name: string;
  path: string;
  has_fetch_script: boolean;
  has_import_script: boolean;
  environment: string;
}

export async function listCurators(): Promise<any> {
  try {
    const dirs = await readdir(CURATOR_BASE_PATH, { withFileTypes: true });
    const curators: Curator[] = [];

    for (const dir of dirs) {
      if (!dir.isDirectory()) continue;

      const curatorPath = join(CURATOR_BASE_PATH, dir.name);
      const scriptsPath = join(curatorPath, "scripts");

      let hasFetch = false;
      let hasImport = false;
      let environment = "unknown";

      try {
        const scripts = await readdir(scriptsPath);
        hasFetch = scripts.includes("fetch_data.py");
        hasImport = scripts.includes("import_items.py");

        // Check secrets.env for environment
        try {
          const secretsContent = await readFile(join(curatorPath, "secrets.env"), "utf-8");
          if (secretsContent.includes("127.0.0.1") || secretsContent.includes("localhost")) {
            environment = "local";
          } else if (secretsContent.includes("supabase.co")) {
            environment = "prod";
          }
        } catch {
          // No secrets.env, environment stays "unknown"
        }
      } catch {
        // No scripts directory, flags stay false
      }

      curators.push({
        name: dir.name,
        path: curatorPath,
        has_fetch_script: hasFetch,
        has_import_script: hasImport,
        environment
      });
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          curators
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: err.message,
          curators: []
        }, null, 2)
      }]
    };
  }
}

export async function getCuratorConfig(args: { name: string }): Promise<any> {
  try {
    const { name } = args;

    if (!name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: "Missing required field: name"
          }, null, 2)
        }]
      };
    }

    const curatorPath = join(CURATOR_BASE_PATH, name);

    // Read plan.md
    let plan = "";
    try {
      plan = await readFile(join(curatorPath, "plan.md"), "utf-8");
    } catch {
      plan = "No plan.md found";
    }

    // Read config.json
    let config: any = {};
    try {
      const configContent = await readFile(join(curatorPath, "config.json"), "utf-8");
      config = JSON.parse(configContent);
    } catch {
      config = {};
    }

    // Extract collection_id and data_source from config
    let collection_id = null;
    let data_source = null;

    // Check if config has collection_id or data_source
    if (config.collection_id) {
      collection_id = config.collection_id;
    }

    if (config.data_source) {
      data_source = config.data_source;
    }

    // Also check secrets.env for COLLECTION_ID
    try {
      const secretsContent = await readFile(join(curatorPath, "secrets.env"), "utf-8");
      const collectionMatch = secretsContent.match(/COLLECTION_ID=([^\s]+)/);
      if (collectionMatch) {
        collection_id = collectionMatch[1];
      }
    } catch {
      // No secrets.env
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          name,
          plan,
          config,
          collection_id,
          data_source
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: err.message
        }, null, 2)
      }]
    };
  }
}
