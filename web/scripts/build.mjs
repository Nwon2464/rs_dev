import { copyFile, mkdir } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(webRoot, "..");
const npm = process.platform === "win32" ? "npm.cmd" : "npm";

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run("python3", ["scripts/build_open_options.py"], root);

const publicData = resolve(webRoot, "public", "data");
const openOptionsData = resolve(publicData, "open_options");
await Promise.all([
  mkdir(resolve(openOptionsData, "general"), { recursive: true }),
  mkdir(resolve(openOptionsData, "instandard"), { recursive: true }),
  mkdir(resolve(openOptionsData, "i18n", "ko"), { recursive: true }),
  mkdir(resolve(openOptionsData, "i18n", "ja"), { recursive: true }),
  mkdir(resolve(openOptionsData, "catalogs"), { recursive: true }),
]);
await Promise.all([
  copyFile(resolve(root, "data/processed/open_options/general/open_option_rows.csv"), resolve(openOptionsData, "general/open_option_rows.csv")),
  copyFile(resolve(root, "data/processed/open_options/instandard/catalog.json"), resolve(openOptionsData, "instandard/catalog.json")),
  copyFile(resolve(root, "data/processed/open_options/instandard/open_option_rows.csv"), resolve(openOptionsData, "instandard/open_option_rows.csv")),
  copyFile(resolve(root, "data/processed/open_options/i18n/ko/base_options.json"), resolve(openOptionsData, "i18n/ko/base_options.json")),
  copyFile(resolve(root, "data/processed/open_options/i18n/ja/base_options.json"), resolve(openOptionsData, "i18n/ja/base_options.json")),
  ...["option_tags.json", "equipment_groups.json", "open_equipment_buckets.json", "open_metadata.json"].map((name) => copyFile(resolve(root, "data/processed/open_options/catalogs", name), resolve(openOptionsData, "catalogs", name))),
]);

run(npm, ["run", "build"], webRoot);
