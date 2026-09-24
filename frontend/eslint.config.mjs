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
} catch {
  // plugin optional — lint still passes without it
}

export default [
  {
    ignores: ["build/**", "node_modules/**", "public/**", "dist/**", "**/*.min.js"]
  },
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
    // Node/CommonJS toolchain files (craco, tailwind, postcss, health-check plugins)
    files: ["*.config.js", "craco.config.js", "postcss.config.js", "tailwind.config.js", "plugins/**/*.js", "scripts/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "commonjs",
      globals: {
        require: "readonly",
        module: "readonly",
        exports: "readonly",
        process: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        console: "readonly",
        setTimeout: "readonly",
        setInterval: "readonly",
        clearTimeout: "readonly",
        clearInterval: "readonly",
        Buffer: "readonly",
        global: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "off",
      "no-undef": "off",
      "no-empty": "off"
    }
  },
  {
    // the config file itself
    files: ["eslint.config.mjs"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module" },
    rules: { "no-unused-vars": "off" }
  }
];
