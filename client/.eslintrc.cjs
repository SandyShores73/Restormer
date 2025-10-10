module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true
    }
  },
  plugins: ["@typescript-eslint", "react-refresh"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }]
  },
  ignorePatterns: ["dist", "electron/*.js"],
  settings: {
    react: {
      version: "detect"
    }
  }
};
