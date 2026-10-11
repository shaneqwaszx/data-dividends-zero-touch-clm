import { defineConfig } from "@playwright/test";
import canonical from "./playwright.config";

export default defineConfig({
  ...canonical,
  testDir: "./evidence-tests",
  testMatch: "*.evidence.ts",
});
