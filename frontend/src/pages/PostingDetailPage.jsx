import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { postingsApi, applicationsApi, anumatiApi } from "../api/resources";
import { useAuth } from "../auth/AuthContext";

export default function PostingDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [posting, setPosting] = useState(null);
  const [anumatiLinked, setAnumatiLinked] = useState(true); // assume linked until known, avoids a flash
  const [coverNote, setCoverNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function load() {
    postingsApi.get(id).then(setPosting);
    if (user?.role === "student") {
      anumatiApi.status().then((s) => setAnumatiLinked(s.user_linked));
    }
  }

  useEffect(load, [id]);

  async function handleApply(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await applicationsApi.apply(posting.id, coverNote);
      load();
    } catch (err) {
      setError(err?.response?.data?.posting?.[0] || "Could not submit application.");
    } finally {
      setBusy(false);
    }
  }

  if (!posting) return <p className="text-ink/40">Loading…</p>;

  return (
    <div className="max-w-2xl">
      <button onClick={() => navigate(-1)} className="text-sm text-navy-600 mb-4">
        ← Back
      </button>

      <h1 className="font-display text-3xl font-semibold text-navy-900">{posting.title}</h1>
      <p className="text-ink/50 mt-1">
        {posting.institution?.name}
        {posting.lab && ` · ${posting.lab}`}
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 mb-6">
        <Stat label="Duration" value={`${posting.duration_weeks} wks`} />
        <Stat label="Stipend" value={`₹${posting.stipend?.toLocaleString("en-IN")}/mo`} />
        <Stat label="Deadline" value={posting.application_deadline} />
        <Stat label="Applicants" value={posting.application_count} />
      </div>

      <Section title="Description">{posting.description}</Section>
      {posting.eligibility && <Section title="Eligibility">{posting.eligibility}</Section>}
      {posting.required_documents?.length > 0 && (
        <Section title="Documents you'll eventually need to share">
          <ul className="list-disc list-inside text-ink/70">
            {posting.required_documents.map((d) => (
              <li key={d}>{d.replaceAll("_", " ")}</li>
            ))}
          </ul>
          <p className="text-xs text-ink/40 mt-2">
            Shared through your linked Anumati locker once you're admitted.
          </p>
        </Section>
      )}

      {user?.role === "student" && !anumatiLinked && !posting.has_applied && (
        <div className="mb-6 bg-amber-100/50 border border-amber-400/40 rounded-xl px-4 py-3 text-sm text-ink/70">
          You haven't linked an Anumati locker yet. You can still apply, but
          document sharing won't start until you{" "}
          <Link to="/anumati" className="text-navy-700 font-medium underline">
            link one
          </Link>
          .
        </div>
      )}

      {user?.role === "student" && (
        <div className="mt-8 border-t border-navy-100 pt-6">
          {posting.has_applied ? (
            <p className="text-moss-600 font-medium">
              ✓ You've already applied to this posting.
            </p>
          ) : !posting.is_open ? (
            <p className="text-ink/40">This posting is closed to new applications.</p>
          ) : (
            <form onSubmit={handleApply} className="space-y-3">
              <label className="block text-sm font-medium text-ink/70">
                Cover note (optional)
              </label>
              <textarea
                className="w-full rounded-lg border border-navy-100 px-3 py-2 h-28"
                value={coverNote}
                onChange={(e) => setCoverNote(e.target.value)}
                placeholder="Why are you a good fit for this internship?"
              />
              {error && <p className="text-sm text-rust-600">{error}</p>}
              <button
                disabled={busy}
                className="bg-navy-700 hover:bg-navy-600 text-white font-medium rounded-lg px-5 py-2 disabled:opacity-60"
              >
                {busy ? "Submitting…" : "Apply"}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-navy-50 rounded-lg px-3 py-2">
      <div className="text-xs text-navy-400 uppercase tracking-wide">{label}</div>
      <div className="font-semibold text-navy-900">{value}</div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-5">
      <h3 className="font-display text-base font-semibold text-navy-900 mb-1">{title}</h3>
      <div className="text-ink/70 whitespace-pre-line">{children}</div>
    </div>
  );
}
