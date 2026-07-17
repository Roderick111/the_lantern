import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import type { Language } from "../../src/domain/types";
import { tm } from "../../src/i18n/miniapp_ui";
import { ensureSession, isApiError, readyMiniApp } from "./api";
import {
  CasebookPage,
  EvidencePage,
  VerdictPage,
  WitnessesPage,
} from "./pages";
import { ErrorState, Loading } from "./ui";

export function App() {
  const [lang, setLang] = useState<Language>("en");
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<import("./api").ApiError | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    readyMiniApp();
    // startapp deep link: tgWebAppStartParam or hash already set by button URL
    const params = new URLSearchParams(window.location.search);
    const start = params.get("tgWebAppStartParam") ?? params.get("startapp");
    if (start && ["casebook", "evidence", "witnesses", "verdict"].includes(start)) {
      navigate(`/${start}`, { replace: true });
    }

    let cancelled = false;
    void (async () => {
      const res = await ensureSession();
      if (cancelled) return;
      if (isApiError(res)) {
        setErr(res);
        setReady(true);
        return;
      }
      setLang(res.language);
      setReady(true);
    })();

    const w = window as unknown as {
      Telegram?: {
        WebApp?: {
          BackButton?: {
            show: () => void;
            hide: () => void;
            onClick: (cb: () => void) => void;
            offClick: (cb: () => void) => void;
          };
        };
      };
    };
    const bb = w.Telegram?.WebApp?.BackButton;
    const onBack = () => navigate(-1);
    bb?.show();
    bb?.onClick(onBack);
    return () => {
      cancelled = true;
      bb?.offClick(onBack);
      bb?.hide();
    };
  }, [navigate]);

  if (!ready) return <Loading lang={lang} />;
  if (err) {
    return (
      <div>
        <ErrorState
          err={err}
          lang={lang}
          onRetry={() => {
            setReady(false);
            setErr(null);
            void ensureSession().then((res) => {
              if (isApiError(res)) setErr(res);
              else setLang(res.language);
              setReady(true);
            });
          }}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <Routes>
        <Route path="/" element={<CasebookPage lang={lang} />} />
        <Route path="/casebook" element={<CasebookPage lang={lang} />} />
        <Route path="/evidence" element={<EvidencePage lang={lang} />} />
        <Route path="/witnesses" element={<WitnessesPage lang={lang} />} />
        <Route path="/verdict" element={<VerdictPage lang={lang} />} />
      </Routes>
      <nav className="nav" aria-label={tm(lang, "app_title")}>
        <NavLink to="/casebook">{tm(lang, "nav_casebook")}</NavLink>
        <NavLink to="/evidence">{tm(lang, "nav_evidence")}</NavLink>
        <NavLink to="/witnesses">{tm(lang, "nav_witnesses")}</NavLink>
        <NavLink to="/verdict">{tm(lang, "nav_verdict")}</NavLink>
      </nav>
    </div>
  );
}
