import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { anumatiApi } from "../api/resources";

const CALLBACK_MESSAGES = {
  success: { text: "Linked successfully.", classes: "bg-moss-100/50 border-moss-500/40" },
  denied: {
    text: "Linking was cancelled on Anumati's side.",
    classes: "bg-amber-100/50 border-amber-500/40",
  },
  error: {
    text: "Something went wrong completing the link.",
    classes: "bg-rust-100/50 border-rust-500/40",
  },
};

export default function LinkAnumatiPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();

  function load() {
    setLoading(true);
    anumatiApi.status().then(setStatus).finally(() => setLoading(false));
  }

  useEffect(load, []);

  const linked = searchParams.get("linked");
  const reason = searchParams.get("reason");
  const callbackMessage = linked ? CALLBACK_MESSAGES[linked] : null;

  useEffect(() => {
    if (linked) {
      // clear the query params once shown, so a refresh doesn't re-show the banner
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linked]);

  if (loading || !status) return <p className="text-ink/40">Loading…</p>;

  return (
    <div className="max-w-xl">
      <h1 className="font-display text-3xl font-semibold text-navy-900 mb-1">
        Anumati
      </h1>
      <p className="text-ink/50 mb-6">
        SRIP uses Anumati only for document sharing — the way an e-commerce
        app uses a UPI handler only for payment. Linking sends you to
        Anumati's own site to approve it; SRIP never sees your password.
      </p>

      {callbackMessage && (
        <div className={`mb-6 rounded-xl px-4 py-3 text-sm border ${callbackMessage.classes}`}>
          {callbackMessage.text}
          {reason && <span className="text-ink/50"> ({reason})</span>}
        </div>
      )}

      {user.role === "student" && (
        <StudentLinkCard status={status} onChange={load} />
      )}

      {user.role === "institution_admin" && (
        <InstitutionLinkCard status={status} onChange={load} />
      )}

      {user.role === "faculty" && (
        <div className="bg-paper-raised border border-navy-100 rounded-xl p-4">
          <p className="text-sm text-ink/60">
            Your institution's Anumati admissions locker is{" "}
            {status.institution_linked ? (
              <span className="text-moss-600 font-medium">linked</span>
            ) : (
              <span className="text-rust-600 font-medium">not linked yet</span>
            )}
            . Only an institution admin can link or change it.
          </p>
        </div>
      )}
    </div>
  );
}

function OAuthLinkButton({ label = "Link with Anumati ↗" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setBusy(true);
    setError("");
    try {
      const { authorize_url } = await anumatiApi.oauthStart();
      window.location.href = authorize_url;
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not start linking.");
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={busy}
        className="bg-navy-700 hover:bg-navy-600 text-white font-medium rounded-lg px-5 py-2 disabled:opacity-60"
      >
        {busy ? "Redirecting…" : label}
      </button>
      {error && <p className="text-sm text-rust-600 mt-2">{error}</p>}
    </div>
  );
}


function StudentLinkCard({ status, onChange }) {
  const [form, setForm] = useState({
    anumati_username: "",
    anumati_password: "",
    locker_name: "Academic",
  });
  const [showVerify, setShowVerify] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setWarning("");
    try {
      const res = await anumatiApi.linkStudent(
        form.anumati_username,
        form.locker_name,
        showVerify ? form.anumati_password : undefined
      );
      if (res.warning) setWarning(res.warning);
      setForm({ ...form, anumati_password: "" });
      onChange();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not link your Anumati locker.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnlink() {
    if (!confirm("Unlink your Anumati locker? You'll need to relink before your next application can share documents.")) return;
    await anumatiApi.unlinkStudent();
    onChange();
  }

  if (status.user_linked) {
    return (
      <div className="bg-paper-raised border border-moss-500/30 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-moss-600 font-medium">✓ Locker linked</p>
          {status.user_verified ? (
            <span className="status-pill bg-moss-100 text-moss-600">Verified</span>
          ) : (
            <span className="status-pill bg-amber-100 text-amber-600">Unverified</span>
          )}
        </div>
        <p className="text-sm text-ink/60">
          Locker: <span className="font-medium text-ink">{status.user_locker_name}</span>
        </p>
        <p className="text-xs text-ink/40 mt-1">
          Linked {new Date(status.user_linked_at).toLocaleString()}
        </p>
        {!status.user_verified && (
          <p className="text-xs text-amber-600 mt-3">
            SRIP hasn't confirmed this locker with Anumati — it was entered
            after you linked it yourself on the Anumati portal. Relink below
            with the optional password field if you want SRIP to verify it.
          </p>
        )}
        <button
          onClick={handleUnlink}
          className="text-sm text-rust-600 font-medium mt-4"
        >
          Unlink
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-paper-raised border border-navy-100 rounded-xl p-5">
        <p className="text-sm text-ink/60 mb-3">
          You'll be sent to Anumati's own site to log in and approve linking
          one of your lockers. SRIP never sees your password — Anumati
          confirms the link directly.
        </p>
        <OAuthLinkButton />
      </div>

      <details className="bg-paper-raised border border-navy-100 rounded-xl p-5">
        <summary className="text-sm font-medium text-ink cursor-pointer">
          Anumati not responding? Link manually instead
        </summary>
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-sm font-medium text-ink mb-1">Step 1 — Open Anumati</p>
            <p className="text-sm text-ink/60 mb-3">
              Log in (or sign up) on Anumati's own site and create or note a
              locker there — SRIP never sees your Anumati password this way.
            </p>
            <a
              href={status.portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-ink/10 hover:bg-ink/20 text-ink font-medium rounded-lg px-5 py-2"
            >
              Open Anumati ↗
            </a>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 border-t border-navy-100 pt-4">
            <p className="text-sm font-medium text-ink">Step 2 — Confirm your locker</p>
            <p className="text-sm text-ink/60">
              Type back the Anumati username and locker name from step 1.
              This is a self-attested link unless you also verify with your
              password below.
            </p>
            <Field label="Anumati username">
              <input
                className="w-full rounded-lg border border-navy-100 px-3 py-2"
                value={form.anumati_username}
                onChange={(e) => setForm({ ...form, anumati_username: e.target.value })}
                required
              />
            </Field>
            <Field label="Locker name">
              <input
                className="w-full rounded-lg border border-navy-100 px-3 py-2"
                value={form.locker_name}
                onChange={(e) => setForm({ ...form, locker_name: e.target.value })}
              />
            </Field>

            <button
              type="button"
              onClick={() => setShowVerify(!showVerify)}
              className="text-sm text-navy-600 font-medium"
            >
              {showVerify ? "− Skip verification" : "+ Optional: verify immediately with your password"}
            </button>

            {showVerify && (
              <Field label="Anumati password (used once, never stored)">
                <input
                  type="password"
                  className="w-full rounded-lg border border-navy-100 px-3 py-2"
                  value={form.anumati_password}
                  onChange={(e) => setForm({ ...form, anumati_password: e.target.value })}
                />
              </Field>
            )}

            {error && <p className="text-sm text-rust-600">{error}</p>}
            {warning && <p className="text-sm text-amber-600">{warning}</p>}
            <button
              disabled={busy}
              className="bg-ink/10 hover:bg-ink/20 text-ink font-medium rounded-lg px-5 py-2 disabled:opacity-60"
            >
              {busy ? "Linking…" : "Confirm link"}
            </button>
          </form>
        </div>
      </details>
    </div>
  );
}

function InstitutionLinkCard({ status, onChange }) {
  const [form, setForm] = useState({
    anumati_username: "",
    anumati_password: "",
    locker_name: "Admissions",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setWarning("");
    try {
      const res = await anumatiApi.linkInstitution(
        form.anumati_username,
        form.anumati_password,
        form.locker_name
      );
      if (res.warning) setWarning(res.warning);
      setForm({ ...form, anumati_password: "" });
      onChange();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not link the institution's Anumati locker.");
    } finally {
      setBusy(false);
    }
  }

  if (status.institution_linked) {
    return (
      <div className="bg-paper-raised border border-moss-500/30 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-moss-600 font-medium">✓ Admissions locker linked</p>
          {status.institution_linked_via_oauth ? (
            <span className="status-pill bg-moss-100 text-moss-600">Via Anumati OAuth</span>
          ) : (
            <span className="status-pill bg-amber-100 text-amber-600">Manual (stored password)</span>
          )}
        </div>
        <p className="text-sm text-ink/60">
          Locker: <span className="font-medium text-ink">{status.institution_locker_name}</span>
        </p>
        <p className="text-xs text-ink/40 mt-1">
          Linked {new Date(status.institution_linked_at).toLocaleString()}
        </p>
        <p className="text-xs text-ink/40 mt-3">
          {status.institution_linked_via_oauth
            ? "SRIP holds a revocable Anumati refresh token, not your password."
            : "Relinking via Anumati OAuth (below) replaces the stored password with a revocable token."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-paper-raised border border-navy-100 rounded-xl p-5">
        <p className="text-sm text-ink/60 mb-3">
          Log in to Anumati as your institution's account and approve the
          link. SRIP receives a revocable token, never your password.
        </p>
        <OAuthLinkButton label="Link institution with Anumati ↗" />
      </div>

      <details className="bg-paper-raised border border-navy-100 rounded-xl p-5">
        <summary className="text-sm font-medium text-ink cursor-pointer">
          Anumati not responding? Link manually instead
        </summary>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <p className="text-sm text-ink/60">
            This links your institution's Anumati service account directly.
            Unlike the OAuth flow above, this password <em>is</em> stored
            (encrypted) — see the architecture notes for why.
          </p>
          <Field label="Anumati username (institution account)">
            <input
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.anumati_username}
              onChange={(e) => setForm({ ...form, anumati_username: e.target.value })}
              required
            />
          </Field>
          <Field label="Anumati password">
            <input
              type="password"
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.anumati_password}
              onChange={(e) => setForm({ ...form, anumati_password: e.target.value })}
              required
            />
          </Field>
          <Field label="Admissions locker name">
            <input
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.locker_name}
              onChange={(e) => setForm({ ...form, locker_name: e.target.value })}
            />
          </Field>
          {error && <p className="text-sm text-rust-600">{error}</p>}
          {warning && <p className="text-sm text-amber-600">{warning}</p>}
          <button
            disabled={busy}
            className="bg-ink/10 hover:bg-ink/20 text-ink font-medium rounded-lg px-5 py-2 disabled:opacity-60"
          >
            {busy ? "Linking…" : "Link admissions locker"}
          </button>
        </form>
      </details>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-ink/70 mb-1">{label}</label>
      {children}
    </div>
  );
}
