import expoConfig from "eslint-config-expo/flat.js";

export default [
  ...expoConfig,
  {
    // Place any custom rules or overrides here
    rules: {
      "no-console": "warn",
    },
  },
];
