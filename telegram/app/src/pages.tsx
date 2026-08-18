import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { Language } from "../../src/domain/types";
import {
  closeMiniApp,
  getLanguage,
  isApiError,
  miniApi,
  newRequestId,
  type Casebook,
  type EvidenceList,
  type VerdictOptions,
  type WitnessList,
} from "./api";
import { Banner, ErrorState, Loading, useT } from "./ui";

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Try the legacy WebView fallback below.
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  }
  textarea.remove();
  return copied;
}

export function CasebookPage({ lang }: { lang: Language }) {
  const t = useT(lang);
  const [data, setData] = useState<Casebook | null>(null);
  const [err, setErr] = useState<import("./api").ApiError | null>(null);
  const [copyStatus, setCopyStatus] = useState<{
    riteId: string;
    copied: boolean;
  } | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const res = await miniApi.casebook();
    if (isApiError(res)) setErr(res);
    else setData(res);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (err) return <ErrorState err={err} lang={lang} onRetry={load} />;
  if (!data) return <Loading lang={lang} />;

  return (
    <div className="page">
      <h1>{data.title}</h1>
      <p className="lead">{data.synopsis}</p>
      <div className="stat-card">
        <div className="row">
          <span>{t("location")}</span>
          <strong>{data.current_location.name}</strong>
        </div>
        <div className="row">
          <span>{t("turns")}</span>
          <strong>
            {data.llm_turns_used}/{data.llm_turns_limit}
          </strong>
        </div>
        <div className="row">
          <span>{t("attempts")}</span>
          <strong>{data.verdict_attempts_remaining}</strong>
        </div>
        {data.case_solved ? <p>{t("solved")}</p> : null}
      </div>
      <h2>{t("visited")}</h2>
      {data.visited_locations.length === 0 ? (
        <p className="empty">{t("empty_visited")}</p>
      ) : (
        data.visited_locations.map((l) => (
          <div className="card" key={l.id}>
            {l.name}
          </div>
        ))
      )}
      <h2>{t("rites")}</h2>
      <p className="hint" style={{ marginBottom: 10 }}>
        {t("rites_hint")}
      </p>
      {data.rites.map((r) => (
        <button
          className="card rite-card"
          key={r.id}
          type="button"
          aria-label={`${t("copy_rite")}: ${r.name}`}
          onClick={async () => {
            const copied = await copyText(r.name);
            setCopyStatus({ riteId: r.id, copied });
          }}
        >
          <strong>
            {r.name}
            {r.id === "mnemonic_delving" ? (
              <span className="badge">{t("restricted")}</span>
            ) : null}
          </strong>
          <p className="hint">{r.help}</p>
          {copyStatus?.riteId === r.id ? (
            <p className="rite-copy-status" aria-live="polite">
              {copyStatus.copied ? t("rite_copied") : t("rite_copy_failed")}
            </p>
          ) : null}
        </button>
      ))}
    </div>
  );
}

export function EvidencePage({ lang }: { lang: Language }) {
  const t = useT(lang);
  const [params] = useSearchParams();
  const presentMode = params.get("present") === "1";
  const [data, setData] = useState<EvidenceList | null>(null);
  const [witnessId, setWitnessId] = useState<string | null>(null);
  const [err, setErr] = useState<import("./api").ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    const [ev, wit] = await Promise.all([miniApi.evidence(), miniApi.witnesses()]);
    if (isApiError(ev)) {
      setErr(ev);
      return;
    }
    setData(ev);
    if (!isApiError(wit)) setWitnessId(wit.selected_witness_id);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (err) return <ErrorState err={err} lang={lang} onRetry={load} />;
  if (!data) return <Loading lang={lang} />;
  if (data.evidence.length === 0) {
    return <Banner>{t("empty_evidence")}</Banner>;
  }

  return (
    <div className="page">
      <h1>{t("nav_evidence")}</h1>
      {data.evidence.map((e) => (
        <div className="card" key={e.id}>
          <strong>{e.name}</strong>
          <p className="meta">
            {e.type} · {e.location_name}
          </p>
          <p className="hint">{e.description}</p>
          {presentMode && witnessId ? (
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                const res = await miniApi.presentEvidence(witnessId, e.id);
                setBusy(false);
                if (isApiError(res)) {
                  setErr(res);
                  return;
                }
                closeMiniApp();
              }}
            >
              {t("present")}
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function WitnessesPage({ lang }: { lang: Language }) {
  const t = useT(lang);
  const [data, setData] = useState<WitnessList | null>(null);
  const [err, setErr] = useState<import("./api").ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    const res = await miniApi.witnesses();
    if (isApiError(res)) setErr(res);
    else setData(res);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (err) return <ErrorState err={err} lang={lang} onRetry={load} />;
  if (!data) return <Loading lang={lang} />;

  return (
    <div className="page">
      <h1>{t("nav_witnesses")}</h1>
      {data.witnesses.map((w) => (
        <div className={`card ${w.selected ? "selected" : ""}`} key={w.id}>
          <strong>
            {w.name}
            {w.selected ? (
              <span className="badge" style={{ background: "color-mix(in srgb, var(--tg-theme-link-color) 35%, transparent)" }}>
                {t("selected")}
              </span>
            ) : null}
          </strong>
          <p className="hint">{w.bio}</p>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              const res = await miniApi.selectWitness(w.id);
              setBusy(false);
              if (isApiError(res)) {
                setErr(res);
                return;
              }
              closeMiniApp();
            }}
          >
            {t("select_witness")}
          </button>
        </div>
      ))}
    </div>
  );
}

export function VerdictPage({ lang }: { lang: Language }) {
  const t = useT(lang);
  const [opts, setOpts] = useState<VerdictOptions | null>(null);
  const [suspect, setSuspect] = useState("");
  const [cited, setCited] = useState<Set<string>>(new Set());
  const [reasoning, setReasoning] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [queued, setQueued] = useState(false);
  const [err, setErr] = useState<import("./api").ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [requestId] = useState(() => newRequestId("ma-verdict"));
  const [validation, setValidation] = useState("");

  const load = useCallback(async () => {
    setErr(null);
    const res = await miniApi.verdictOptions();
    if (isApiError(res)) setErr(res);
    else setOpts(res);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (err) return <ErrorState err={err} lang={lang} onRetry={load} />;
  if (!opts) return <Loading lang={lang} />;

  if (queued) {
    return (
      <div className="page">
        <h1>{t("verdict_title")}</h1>
        <Banner>{t("close_hint")}</Banner>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>{t("verdict_title")}</h1>
      {opts.case_solved ? <Banner>{t("solved")}</Banner> : null}
      {validation ? <Banner kind="error">{validation}</Banner> : null}

      <label htmlFor="suspect">{t("verdict_suspect")}</label>
      <select
        id="suspect"
        value={suspect}
        onChange={(e) => setSuspect(e.target.value)}
        disabled={busy}
      >
        <option value="">—</option>
        {opts.suspects.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      <label>{t("verdict_evidence")}</label>
      <div className="checks">
        {opts.evidence.map((e) => (
          <label key={e.id}>
            <input
              type="checkbox"
              checked={cited.has(e.id)}
              disabled={busy}
              onChange={() => {
                setCited((prev) => {
                  const n = new Set(prev);
                  if (n.has(e.id)) n.delete(e.id);
                  else n.add(e.id);
                  return n;
                });
              }}
            />
            {e.name}
          </label>
        ))}
      </div>

      <label htmlFor="reason">{t("verdict_reasoning")}</label>
      <textarea
        id="reason"
        rows={5}
        value={reasoning}
        disabled={busy}
        onChange={(e) => setReasoning(e.target.value)}
      />

      {!confirm ? (
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (!suspect) {
              setValidation(t("validation_suspect"));
              return;
            }
            if (!reasoning.trim()) {
              setValidation(t("validation_reasoning"));
              return;
            }
            setValidation("");
            setConfirm(true);
          }}
        >
          {t("verdict_submit")}
        </button>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setValidation("");
            const res = await miniApi.submitVerdict({
              accused_suspect_id: suspect,
              evidence_cited: [...cited],
              reasoning: reasoning.trim(),
              request_id: requestId,
            });
            setBusy(false);
            if (isApiError(res)) {
              setErr(res);
              setConfirm(false);
              return;
            }
            setQueued(true);
            closeMiniApp();
          }}
        >
          {t("verdict_confirm")}
        </button>
      )}
    </div>
  );
}

export function langOrDefault(): Language {
  return getLanguage();
}
