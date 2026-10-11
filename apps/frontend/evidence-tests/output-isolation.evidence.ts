import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { browserOutputDirectory, retainedEvidencePath } from "../playwright.config";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const ownedRoot = path.join(root, "tmp/browser-evidence");
let priorArtifact: string | undefined;

test("generated evidence uses a fresh task-owned invocation root", async ({}, info) => {
  const relative = path.relative(ownedRoot, info.project.outputDir);
  expect(relative).not.toMatch(/^\.\./);
  expect(path.isAbsolute(relative)).toBe(false);
  expect(relative.split(path.sep)[0]).toMatch(/^[0-9a-f-]{36}$/);
});

test("manual synthetic evidence is retained without enabling automatic capture", async ({}, info) => {
  expect(info.config.preserveOutput).toBe("never");
  expect(info.project.use.trace).toBe("off");
  expect(info.project.use.video).toBe("off");
  expect(info.project.use.screenshot).toBe("off");
  expect(info.project.retries).toBe(0);
});

test("outputPath rejects traversal outside the owning test directory", async ({}, info) => {
  expect(() => info.outputPath("..", "escaped.json")).toThrow();
  expect(() => retainedEvidencePath("..", "escaped.json")).toThrow();
});

test("dummy evidence cannot replace a frozen historical record", async ({}, info) => {
  const frozen = path.join(root, ".ai-pipeline/reports/SPONSOR_DEMO_REGRESSION_EVIDENCE/group-2.json");
  const hash = () => createHash("sha256").update(fs.readFileSync(frozen)).digest("hex");
  const before = hash();
  const destination = retainedEvidencePath("blocker-regression", "group-2.json");
  priorArtifact = destination;
  expect(path.relative(info.project.outputDir, destination)).toMatch(/^\.\./);
  expect(destination).not.toBe(frozen);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.writeFileSync(destination, JSON.stringify({ synthetic: true, count: 1 }));
  expect(hash()).toBe(before);
  expect(JSON.parse(fs.readFileSync(destination, "utf8"))).toEqual({ synthetic: true, count: 1 });
});

test("separate invocations never reuse a prior output directory", async ({}) => {
  const first = browserOutputDirectory();
  const second = browserOutputDirectory();
  expect(first).not.toBe(second);
  for (const directory of [first, second]) {
    const relative = path.relative(ownedRoot, directory);
    expect(relative).not.toMatch(/^\.\./);
    expect(path.isAbsolute(relative)).toBe(false);
  }
});

test("unsupported output ownership fails before any historical path is written", async ({}, info) => {
  const original = info.project.outputDir;
  try {
    info.project.outputDir = path.join(root, ".ai-pipeline/reports");
    expect(() => retainedEvidencePath("unexpected.json")).toThrow("owned invocation output directory");
  } finally {
    info.project.outputDir = original;
  }
});

test("identical evidence filenames from different tests preserve both records", async ({}) => {
  expect(priorArtifact).toBeDefined();
  const current = retainedEvidencePath("blocker-regression", "group-2.json");
  expect(current).not.toBe(priorArtifact);
  fs.mkdirSync(path.dirname(current), { recursive: true });
  fs.writeFileSync(current, JSON.stringify({ synthetic: true, count: 2 }));
  expect(JSON.parse(fs.readFileSync(priorArtifact!, "utf8"))).toEqual({ synthetic: true, count: 1 });
  expect(JSON.parse(fs.readFileSync(current, "utf8"))).toEqual({ synthetic: true, count: 2 });
});
