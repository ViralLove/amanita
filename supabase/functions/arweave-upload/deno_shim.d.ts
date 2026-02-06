/**
 * Декларации для IDE (TypeScript LSP): URL-модуль serve.
 * Подключается через /// <reference /> в index.ts. Глобал Deno не объявляем,
 * чтобы deno check не конфликтовал с lib.deno.ns.d.ts.
 */

declare module "https://deno.land/std@0.168.0/http/server.ts" {
  export function serve(
    handler: (req: Request) => Response | Promise<Response>,
    options?: { port?: number; hostname?: string }
  ): Promise<void>;
}

