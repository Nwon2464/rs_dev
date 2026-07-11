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

run("python3", ["scripts/collect_instandard_equipment.py"], root);
run("python3", [
  "scripts/collect_equipment_open_options.py",
  "--classify-converters",
  "--output",
  "data/processed/equipment_converter_type_options.csv",
], root);
run("python3", ["scripts/export_instandard_open_options.py"], root);
run("python3", ["scripts/validate_instandard_equipment.py"], root);

const publicData = resolve(webRoot, "public", "data");
await mkdir(publicData, { recursive: true });
await Promise.all([
  copyFile(resolve(root, "data/processed/instandard_equipment.json"), resolve(publicData, "instandard_equipment.json")),
  copyFile(resolve(root, "data/processed/equipment_converter_type_options.csv"), resolve(publicData, "equipment_converter_type_options.csv")),
  copyFile(resolve(root, "data/processed/instandard_open_option_rows.csv"), resolve(publicData, "instandard_open_option_rows.csv")),
]);

run(npm, ["run", "build"], webRoot);
