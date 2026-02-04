/**
 * Глобал Deno для IDE (TypeScript LSP). Подключается только через tsconfig include.
 * Не ссылаем из index.ts, чтобы deno check не загружал и не конфликтовал с lib.deno.ns.d.ts.
 */

declare global {
  const Deno: {
    env: { get(key: string): string | undefined };
    readTextFile(path: string): Promise<string>;
  };
}

export {};
