import { spawn } from "child_process";
import { readFile } from "fs/promises";
import { join } from "path";
import { supabase } from "../../index.js";

const CURATOR_BASE_PATH = join(process.cwd(), ".curator/curators");
const SCRIPT_TIMEOUT_MS = 60000; // 60 seconds

export async function runCuratorFetch(args: { name: string; options?: Record<string, any> }): Promise<any> {
  try {
    const { name, options } = args;

    if (!name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            status: "error",
            error: "Missing required field: name",
            items_fetched: 0,
            data: null,
            errors: ["Missing required field: name"]
          }, null, 2)
        }]
      };
    }

    const curatorPath = join(CURATOR_BASE_PATH, name);
    const fetchScript = join(curatorPath, "scripts", "fetch_data.py");

    // Build CLI arguments from options object
    const scriptArgs = [fetchScript];
    if (options) {
      for (const [key, value] of Object.entries(options)) {
        // Handle boolean flags (e.g., --dry-run)
        if (typeof value === 'boolean') {
          if (value) {
            scriptArgs.push(`--${key}`);
          }
        }
        // Handle array values (e.g., multiple --series arguments)
        else if (Array.isArray(value)) {
          for (const item of value) {
            scriptArgs.push(`--${key}`);
            scriptArgs.push(String(item));
          }
        }
        // Handle regular key-value pairs
        else {
          scriptArgs.push(`--${key}`);
          scriptArgs.push(String(value));
        }
      }
    }

    // Load curator-specific secrets.env file
    let curatorEnv = { ...process.env };
    try {
      const secretsPath = join(curatorPath, "secrets.env");
      const secretsContent = await readFile(secretsPath, "utf-8");

      // Parse key=value pairs from secrets.env
      for (const line of secretsContent.split('\n')) {
        const trimmed = line.trim();
        // Skip empty lines and comments
        if (!trimmed || trimmed.startsWith('#')) continue;

        const match = trimmed.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
        if (match) {
          const [, key, value] = match;
          // Remove quotes if present
          curatorEnv[key] = value.replace(/^["']|["']$/g, '');
        }
      }
    } catch (err) {
      // secrets.env is optional - continue without it
    }

    return new Promise((resolve) => {
      const python = spawn("python3", scriptArgs, {
        cwd: curatorPath,
        env: curatorEnv
      });

      let stdout = "";
      let stderr = "";
      let killed = false;

      // Set timeout
      const timeout = setTimeout(() => {
        killed = true;
        python.kill();
        resolve({
          content: [{
            type: "text",
            text: JSON.stringify({
              status: "error",
              error: `Fetch script timed out after ${SCRIPT_TIMEOUT_MS / 1000} seconds`,
              items_fetched: 0,
              data: null,
              errors: [`Timeout after ${SCRIPT_TIMEOUT_MS / 1000}s`]
            }, null, 2)
          }]
        });
      }, SCRIPT_TIMEOUT_MS);

      python.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      python.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      python.on("close", async (code) => {
        clearTimeout(timeout);

        if (killed) {
          return; // Already resolved with timeout error
        }

        if (code !== 0) {
          resolve({
            content: [{
              type: "text",
              text: JSON.stringify({
                status: "error",
                error: `Fetch script exited with code ${code}`,
                items_fetched: 0,
                data: null,
                errors: [stderr || `Exit code ${code}`],
                stdout,
                stderr
              }, null, 2)
            }]
          });
          return;
        }

        // Read fetched_data.json
        try {
          const dataPath = join(curatorPath, "fetched_data.json");
          const dataContent = await readFile(dataPath, "utf-8");
          const data = JSON.parse(dataContent);

          // Count items - handle different data structures
          let itemsCount = 0;
          if (Array.isArray(data)) {
            itemsCount = data.length;
          } else if (data.items && Array.isArray(data.items)) {
            itemsCount = data.items.length;
          } else if (data.data && Array.isArray(data.data)) {
            itemsCount = data.data.length;
          }

          // Return partial data (first 5 items) to avoid huge responses
          let partialData = data;
          if (Array.isArray(data) && data.length > 5) {
            partialData = data.slice(0, 5);
          } else if (data.items && Array.isArray(data.items) && data.items.length > 5) {
            partialData = { ...data, items: data.items.slice(0, 5) };
          } else if (data.data && Array.isArray(data.data) && data.data.length > 5) {
            partialData = { ...data, data: data.data.slice(0, 5) };
          }

          resolve({
            content: [{
              type: "text",
              text: JSON.stringify({
                status: "success",
                items_fetched: itemsCount,
                data: partialData,
                errors: []
              }, null, 2)
            }]
          });
        } catch (err: any) {
          resolve({
            content: [{
              type: "text",
              text: JSON.stringify({
                status: "error",
                error: `Failed to read fetched_data.json: ${err.message}`,
                items_fetched: 0,
                data: null,
                errors: [err.message],
                stdout,
                stderr
              }, null, 2)
            }]
          });
        }
      });
    });

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          status: "error",
          error: err.message,
          items_fetched: 0,
          data: null,
          errors: [err.message]
        }, null, 2)
      }]
    };
  }
}

export async function validateCuratorData(args: { name: string; data?: any }): Promise<any> {
  try {
    const { name, data } = args;

    if (!name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            valid: false,
            warnings: [],
            errors: ["Missing required field: name"]
          }, null, 2)
        }]
      };
    }

    const curatorPath = join(CURATOR_BASE_PATH, name);

    // If data provided, validate it directly, otherwise read from fetched_data.json
    let dataToValidate = data;
    if (!dataToValidate) {
      try {
        const dataPath = join(curatorPath, "fetched_data.json");
        const dataContent = await readFile(dataPath, "utf-8");
        dataToValidate = JSON.parse(dataContent);
      } catch (err: any) {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              valid: false,
              warnings: [],
              errors: [`Failed to read fetched_data.json: ${err.message}`]
            }, null, 2)
          }]
        };
      }
    }

    const warnings: string[] = [];
    const errors: string[] = [];

    // Basic validation
    if (!dataToValidate) {
      errors.push("Data is null or undefined");
    } else if (typeof dataToValidate !== 'object') {
      errors.push("Data is not a valid JSON object");
    } else {
      // Check for common data structures
      const hasItems = dataToValidate.items && Array.isArray(dataToValidate.items);
      const hasData = dataToValidate.data && Array.isArray(dataToValidate.data);
      const isArray = Array.isArray(dataToValidate);

      if (!hasItems && !hasData && !isArray) {
        warnings.push("Data structure doesn't contain 'items' or 'data' array, and is not an array itself");
      }

      // Validate individual items if present
      const items = isArray ? dataToValidate : (dataToValidate.items || dataToValidate.data || []);
      if (items.length === 0) {
        warnings.push("No items found in data");
      } else {
        // Check first few items for required fields
        const sampleSize = Math.min(5, items.length);
        for (let i = 0; i < sampleSize; i++) {
          const item = items[i];
          if (!item.name && !item.title) {
            warnings.push(`Item ${i} missing 'name' or 'title' field`);
          }
        }
      }
    }

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          valid: errors.length === 0,
          warnings,
          errors
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          valid: false,
          warnings: [],
          errors: [err.message]
        }, null, 2)
      }]
    };
  }
}

export async function getCuratorStats(args: { name: string }): Promise<any> {
  try {
    const { name } = args;

    if (!name) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: "Missing required field: name",
            total_items: 0,
            last_import: null,
            items_in_collection: 0
          }, null, 2)
        }]
      };
    }

    const curatorPath = join(CURATOR_BASE_PATH, name);

    // Read collection_id from secrets.env
    let collection_id = null;
    try {
      const secretsContent = await readFile(join(curatorPath, "secrets.env"), "utf-8");
      const collectionMatch = secretsContent.match(/COLLECTION_ID=([^\s]+)/);
      if (collectionMatch) {
        collection_id = collectionMatch[1];
      }
    } catch {
      // No secrets.env
    }

    if (!collection_id) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: "Collection ID not found in secrets.env",
            total_items: 0,
            last_import: null,
            items_in_collection: 0,
            collection_id: null
          }, null, 2)
        }]
      };
    }

    // Get collection entity
    const { data: collection, error: collectionError } = await supabase
      .from("entities")
      .select("id, name, created_at, updated_at")
      .eq("id", collection_id)
      .single();

    if (collectionError || !collection) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: `Collection not found: ${collection_id}`,
            total_items: 0,
            last_import: null,
            items_in_collection: 0,
            collection_id
          }, null, 2)
        }]
      };
    }

    // Count items in collection (via relationships)
    const { count, error: countError } = await supabase
      .from("relationships")
      .select("*", { count: "exact", head: true })
      .eq("from_id", collection_id);

    const itemCount = countError ? 0 : (count || 0);

    // Get most recently created entity in this collection
    const { data: recentItems } = await supabase
      .from("relationships")
      .select("to_id, entities!relationships_to_id_fkey(created_at)")
      .eq("from_id", collection_id)
      .order("created_at", { ascending: false })
      .limit(1);

    const lastImport = recentItems && recentItems.length > 0
      ? (recentItems[0] as any).entities?.created_at
      : null;

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          collection_id,
          collection_name: collection.name,
          total_items: itemCount,
          last_import: lastImport,
          items_in_collection: itemCount,
          collection_created: collection.created_at,
          collection_updated: collection.updated_at
        }, null, 2)
      }]
    };

  } catch (err: any) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: err.message,
          total_items: 0,
          last_import: null,
          items_in_collection: 0
        }, null, 2)
      }]
    };
  }
}
