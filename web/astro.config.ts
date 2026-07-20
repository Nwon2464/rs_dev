import react from "@astrojs/react";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://nwon2464.github.io",
  base: "/rs_dev",
  output: "static",
  trailingSlash: "always",
  integrations: [react()],
});
