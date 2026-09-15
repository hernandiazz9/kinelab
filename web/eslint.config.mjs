import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    // El árbol que se sube a Vercel (`kinelab.tools.publicar`): es una copia de
    // `out/`, ya minificada, y está en `web/.gitignore`. Sin esto, `pnpm lint`
    // pasa a lintear el bundle y devuelve miles de problemas que no son de nadie.
    ".vercel/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
