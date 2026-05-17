import postcss from "postcss";
import { readFileSync } from "node:fs";
import { dirname, join, normalize, relative } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = normalize(fileURLToPath(new URL("..", import.meta.url)));
const entryFile = join(projectRoot, "src/styles.css");
const importPattern = /@import\s+["']([^"']+)["'];/g;

const visited = new Set();
const orderedFiles = [];

function collectImports(filePath) {
  const normalized = normalize(filePath);
  if (visited.has(normalized)) return;
  visited.add(normalized);
  orderedFiles.push(normalized);

  const content = readFileSync(normalized, "utf8");
  for (const match of content.matchAll(importPattern)) {
    collectImports(join(dirname(normalized), match[1]));
  }
}

function splitSelectors(selectorText) {
  const selectors = [];
  let current = "";
  let depth = 0;
  let quote = null;
  let escaped = false;

  for (const character of selectorText) {
    if (escaped) {
      current += character;
      escaped = false;
      continue;
    }

    if (character === "\\") {
      current += character;
      escaped = true;
      continue;
    }

    if (quote) {
      current += character;
      if (character === quote) quote = null;
      continue;
    }

    if (character === '"' || character === "'") {
      current += character;
      quote = character;
      continue;
    }

    if (character === "(" || character === "[" || character === "{") depth += 1;
    if (character === ")" || character === "]" || character === "}") depth = Math.max(0, depth - 1);

    if (character === "," && depth === 0) {
      const selector = current.replace(/\s+/g, " ").trim();
      if (selector) selectors.push(selector);
      current = "";
      continue;
    }

    current += character;
  }

  const selector = current.replace(/\s+/g, " ").trim();
  if (selector) selectors.push(selector);
  return selectors;
}

function contextFor(rule) {
  const contexts = [];
  let node = rule.parent;

  while (node) {
    if (node.type === "atrule") {
      contexts.unshift(`@${node.name} ${node.params}`.trim());
    }
    node = node.parent;
  }

  return contexts.length ? contexts.join(" | ") : "top-level";
}

collectImports(entryFile);

const selectorMap = new Map();
for (const filePath of orderedFiles) {
  const content = readFileSync(filePath, "utf8");
  const relativeFile = relative(projectRoot, filePath);
  const root = postcss.parse(content, { from: filePath });

  root.walkRules((rule) => {
    const context = contextFor(rule);
    for (const selector of splitSelectors(rule.selector)) {
      const key = `${context}||${selector}`;
      const entries = selectorMap.get(key) ?? [];
      entries.push({ file: relativeFile, context, selector });
      selectorMap.set(key, entries);
    }
  });
}

const duplicates = [...selectorMap.values()]
  .filter((entries) => entries.length > 1)
  .map((entries) => ({
    selector: entries[0].selector,
    context: entries[0].context,
    entries,
    files: [...new Set(entries.map((entry) => entry.file))].sort(),
  }))
  .sort((a, b) => b.entries.length - a.entries.length || a.selector.localeCompare(b.selector));

console.log(`css duplicate selector audit: scanned ${orderedFiles.length} imported CSS files`);

if (duplicates.length === 0) {
  console.log("css duplicate selector audit: no duplicate selectors found");
  process.exit(0);
}

console.log(`css duplicate selector audit: ${duplicates.length} duplicate selector entries`);
for (const duplicate of duplicates) {
  const contextSuffix = duplicate.context === "top-level" ? "" : ` @ ${duplicate.context}`;
  console.log(
    `${duplicate.entries.length}x ${duplicate.selector}${contextSuffix} :: ${duplicate.files.join(", ")}`,
  );
}
