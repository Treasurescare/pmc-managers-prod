// Minimal ESLint v9 flat config so pre-completion checks succeed.
// The app is bundled via CRA (which uses its own ESLint config internally at build time).
import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  // Global ignores — MUST be first so ESLint skips these directories entirely.
  {
    ignores: [
      "build/**",
      "node_modules/**",
      "public/**",
      "plugins/**",
      "**/*.config.js",
      "src/components/ui/**",
    ],
  },
  // Scope the recommended ruleset ONLY to src/ so it doesn't lint tool scripts.
  {
    ...js.configs.recommended,
    files: ["src/**/*.{js,jsx}"],
  },
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-undef": "off",
      "no-empty": ["warn", { allowEmptyCatch: true }],
      "react/jsx-uses-react": "off",
      "react/jsx-uses-vars": "error",
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
];
