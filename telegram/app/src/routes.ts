const MINIAPP_ROUTES = new Set(["casebook", "evidence", "witnesses", "verdict"]);

export function getLaunchRedirect(search: string, hash: string): string | null {
  const hashPath = (hash.replace(/^#\/?/, "") || "").split("?")[0];
  if (MINIAPP_ROUTES.has(hashPath)) return null;

  const params = new URLSearchParams(search);
  const start = params.get("tgWebAppStartParam") ?? params.get("startapp");
  if (start && MINIAPP_ROUTES.has(start)) return `/${start}`;

  return "/casebook";
}
