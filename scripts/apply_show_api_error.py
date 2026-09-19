#!/usr/bin/env python3
"""
Bulk-rewrite `toast.error(formatApiError(x))` → `showApiError(x)` and add
`showApiError` to imports from `@/lib/api`.

Safe by design:
- Only touches files that currently import from "@/lib/api" (i.e. app code
  that already knows about `formatApiError`).
- Preserves formatting: only rewrites specific one-liner patterns; leaves
  multi-argument or validation `toast.error("string")` calls alone.
- Idempotent: skips files where the pattern is already migrated.
"""
import os
import re
import sys

ROOT = "/app/frontend/src"

# Match the two common patterns:
#   toast.error(formatApiError(<ident>))
#   toast.error(formatApiError(<ident>) || <expr>)  → we don't touch these
ERR_PATTERNS = [
    (re.compile(r"toast\.error\(\s*formatApiError\(\s*([A-Za-z_][A-Za-z_0-9]*)\s*\)\s*\)"),
     r"showApiError(\1)"),
]

IMPORT_RE = re.compile(
    r'from\s+["\']@/lib/api["\']'
)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def process_file(path):
    src = load(path)
    if "@/lib/api" not in src:
        return False
    if "toast.error(formatApiError" not in src:
        return False
    orig = src
    for pat, repl in ERR_PATTERNS:
        src = pat.sub(repl, src)
    if src == orig:
        return False
    # Ensure `showApiError` is present in the api import line.
    def _fix_import(m):
        line = m.group(0)
        if "showApiError" in line:
            return line
        # Insert into import specifiers
        # Handles: import { a, b } from "@/lib/api"  and  import api, { a } from "@/lib/api"
        return re.sub(
            r"(import\s+(?:[\w$]+\s*,\s*)?\{)([^}]*)(\}\s*from\s+[\"']@/lib/api[\"'])",
            lambda mm: mm.group(1)
                + (mm.group(2).rstrip(", \n\t") + ", showApiError")
                + mm.group(3),
            line,
        )

    import_line_re = re.compile(
        r"import\s+(?:[\w$]+\s*,\s*)?\{[^}]*\}\s*from\s+[\"']@/lib/api[\"'];?"
    )
    m = import_line_re.search(src)
    if m and "showApiError" not in m.group(0):
        src = src[: m.start()] + _fix_import(m) + src[m.end() :]

    save(path, src)
    return True


def main():
    changed = []
    for base, _, files in os.walk(ROOT):
        for name in files:
            if not name.endswith((".jsx", ".js", ".tsx", ".ts")):
                continue
            path = os.path.join(base, name)
            try:
                if process_file(path):
                    changed.append(path)
            except Exception as e:  # noqa
                print(f"skip {path}: {e}", file=sys.stderr)
    print(f"Updated {len(changed)} files:")
    for p in changed:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
