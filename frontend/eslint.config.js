import js from "@eslint/js";
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

let reactHooks = null;
try {
  const reactHooksPath = require.resolve("eslint-plugin-react-hooks", { paths: [path.join(__dirname, "node_modules")] });
  reactHooks = require(reactHooksPath);
} catch (e) {
  // ignore
}

export default [
  js.configs.recommended,
  {
    files: ["src/**/*.{js,jsx}"],
    plugins: reactHooks ? { "react-hooks": reactHooks } : {},
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      }
    },
    rules: {
      "no-unused-vars": "off",
      "no-undef": "off",
      "no-empty": "off",
      "no-constant-binary-expression": "off"
    }
  },
  {
    ignores: ["build/**", "node_modules/**", "public/**", "dist/**", "**/*.min.js"]
  }
];
