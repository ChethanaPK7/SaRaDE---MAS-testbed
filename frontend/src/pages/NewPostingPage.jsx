import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postingsApi } from "../api/resources";

const DOC_OPTIONS = ["transcript", "recommendation_letter", "id_proof", "resume", "portfolio"];

export default function NewPostingPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "",
    lab: "",
    description: "",
    eligibility: "",
    duration_weeks: 8,
    stipend: 10000,
    application_deadline: "",
    required_documents: [],
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function toggleDoc(doc) {
    setForm((f) => ({
      ...f,
      required_documents: f.required_documents.includes(doc)
        ? f.required_documents.filter((d) => d !== doc)
        : [...f.required_documents, doc],
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await postingsApi.create(form);
      navigate(`/postings/${created.id}`);
    } catch (err) {
      const data = err?.response?.data;
      setError(data ? Object.values(data).flat().join(" ") : "Could not create posting.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="font-display text-2xl font-semibold text-navy-900 mb-6">
        New internship posting
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Title">
          <input
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </Field>
        <Field label="Lab">
          <input
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.lab}
            onChange={(e) => setForm({ ...form, lab: e.target.value })}
          />
        </Field>
        <Field label="Description">
          <textarea
            className="w-full rounded-lg border border-navy-100 px-3 py-2 h-24"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
        </Field>
        <Field label="Eligibility">
          <textarea
            className="w-full rounded-lg border border-navy-100 px-3 py-2 h-20"
            value={form.eligibility}
            onChange={(e) => setForm({ ...form, eligibility: e.target.value })}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Duration (weeks)">
            <input
              type="number"
              min={1}
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.duration_weeks}
              onChange={(e) => setForm({ ...form, duration_weeks: Number(e.target.value) })}
            />
          </Field>
          <Field label="Stipend (₹/mo)">
            <input
              type="number"
              min={0}
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.stipend}
              onChange={(e) => setForm({ ...form, stipend: Number(e.target.value) })}
            />
          </Field>
        </div>
        <Field label="Application deadline">
          <input
            type="date"
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.application_deadline}
            onChange={(e) => setForm({ ...form, application_deadline: e.target.value })}
            required
          />
        </Field>
        <Field label="Documents you'll need (shared via Anumati in Phase 2)">
          <div className="flex flex-wrap gap-2">
            {DOC_OPTIONS.map((doc) => (
              <button
                type="button"
                key={doc}
                onClick={() => toggleDoc(doc)}
                className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                  form.required_documents.includes(doc)
                    ? "bg-navy-700 text-white border-navy-700"
                    : "border-navy-100 text-ink/60"
                }`}
              >
                {doc.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        </Field>
        {error && <p className="text-sm text-rust-600">{error}</p>}
        <button
          disabled={busy}
          className="bg-navy-700 hover:bg-navy-600 text-white font-medium rounded-lg px-5 py-2 disabled:opacity-60"
        >
          {busy ? "Publishing…" : "Publish posting"}
        </button>
      </form>
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
