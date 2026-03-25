#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = process.cwd();
const TARGET_DIR = path.join(ROOT, "contracts", "tests");
const ALLOW_TOKEN = "anti-false-success: allow";

const FILE_EXTENSIONS = new Set([".js", ".ts"]);

const RULES = [
    {
        id: "tx-hash-assertion",
        description: "tx.hash-only assertion is forbidden",
        regex: /expect\s*\(\s*(?:tx|txn|transaction)\s*\.\s*hash\s*\)/g,
    },
    {
        id: "promise-catch-swallow",
        description: "swallowed promise error with .catch(() => {}) is forbidden",
        regex: /\.catch\s*\(\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{\s*\}\s*\)/g,
    },
    {
        id: "empty-catch-block",
        description: "empty catch block is forbidden",
        regex: /catch\s*\([^)]*\)\s*\{\s*\}/g,
    },
];

function walk(dir, out = []) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            walk(full, out);
            continue;
        }
        if (!FILE_EXTENSIONS.has(path.extname(entry.name))) continue;
        out.push(full);
    }
    return out;
}

function getLineNumber(source, index) {
    let line = 1;
    for (let i = 0; i < index; i += 1) {
        if (source.charCodeAt(i) === 10) line += 1;
    }
    return line;
}

function hasAllowMarkerNearby(source, index) {
    const lineStart = source.lastIndexOf("\n", index) + 1;
    const lineEndIdx = source.indexOf("\n", index);
    const lineEnd = lineEndIdx === -1 ? source.length : lineEndIdx;
    const lineText = source.slice(lineStart, lineEnd);
    if (lineText.includes(ALLOW_TOKEN)) return true;

    const prevLineStartIdx = source.lastIndexOf("\n", Math.max(0, lineStart - 2));
    const prevLineStart = prevLineStartIdx === -1 ? 0 : prevLineStartIdx + 1;
    const prevLine = source.slice(prevLineStart, lineStart - 1);
    return prevLine.includes(ALLOW_TOKEN);
}

function main() {
    if (!fs.existsSync(TARGET_DIR)) {
        console.error(`[anti-false-success] Target directory not found: ${TARGET_DIR}`);
        process.exit(1);
    }

    const files = walk(TARGET_DIR);
    const violations = [];

    for (const filePath of files) {
        const source = fs.readFileSync(filePath, "utf8");
        for (const rule of RULES) {
            rule.regex.lastIndex = 0;
            let match;
            while ((match = rule.regex.exec(source)) !== null) {
                const idx = match.index;
                if (hasAllowMarkerNearby(source, idx)) continue;
                violations.push({
                    filePath,
                    ruleId: rule.id,
                    description: rule.description,
                    line: getLineNumber(source, idx),
                    snippet: match[0],
                });
            }
        }
    }

    if (violations.length === 0) {
        console.log("[anti-false-success] OK: no forbidden patterns found.");
        return;
    }

    console.error(`[anti-false-success] FAILED: ${violations.length} violation(s) found.`);
    for (const v of violations) {
        const rel = path.relative(ROOT, v.filePath);
        console.error(`- ${rel}:${v.line} [${v.ruleId}] ${v.description}`);
        console.error(`  snippet: ${v.snippet}`);
    }
    console.error(`Hint: use '${ALLOW_TOKEN}' comment only for justified exceptions.`);
    process.exit(1);
}

main();

