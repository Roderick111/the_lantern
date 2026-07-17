import type { ReactNode } from "react";
import type { Language } from "../../src/domain/types";
import { tm, type MiniUiKey } from "../../src/i18n/miniapp_ui";
import type { ApiError } from "./api";

export function useT(lang: Language) {
  return (key: MiniUiKey) => tm(lang, key);
}

export function Banner({
  kind,
  children,
}: {
  kind?: "error" | "info";
  children: ReactNode;
}) {
  return <div className={`banner ${kind === "error" ? "error" : ""}`}>{children}</div>;
}

export function ErrorState({
  err,
  lang,
  onRetry,
}: {
  err: ApiError;
  lang: Language;
  onRetry?: () => void;
}) {
  const t = useT(lang);
  let msg = t("error_generic");
  if (err.error === "offline") msg = t("offline");
  else if (err.error === "session_expired" || err.status === 401) {
    msg = t("session_expired");
  } else if (err.error === "conflict" || err.status === 409) msg = t("conflict");
  else if (err.error === "cap_reached" || err.status === 429) msg = t("cap_reached");
  return (
    <div>
      <Banner kind="error">{msg}</Banner>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          {t("retry")}
        </button>
      ) : null}
    </div>
  );
}

export function Loading({ lang }: { lang: Language }) {
  return <p className="hint">{tm(lang, "loading")}</p>;
}
