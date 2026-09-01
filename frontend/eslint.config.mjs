import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "node_modules/**", "out/**"],
  },
  {
    rules: {
      // The API returns loosely-typed nested agent payloads; `any` at those
      // boundaries is deliberate and checked at runtime by the components.
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  {
    files: ["*.config.{ts,mjs,js}", "tailwind.config.ts"],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
];

export default eslintConfig;
