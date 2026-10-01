import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { applicationsApi, postingsApi } from "../api/resources";
import StatusPill from "../components/StatusPill";
import { ACTION_META } from "../lib/statusMeta";

export default function ReviewPostingApplicantsPage() {
  const { id } = useParams();
  const [posting, setPosting] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");

  function load() {
    setLoading(true);
    Promise.all([
      postingsApi.get(id),
      applicationsApi.list({ posting: id, ...(statusFilter ? { status: statusFilter } : {}) }),
    ])
      .then(([p, apps]) => {
        setPosting(p);
        setApplications(apps.results || apps);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [id, statusFilter]);

  async function handleAction(app, action) {
    if (action === "admit" && !confirm(
      `Admit ${app.student.username}? Every other open applicant to this posting will be auto-rejected.`
    )) {
      return;
    }
    if (action === "reject" && !confirm(`Reject ${app.student.username}?`)) return;

    setBusyId(app.id);
    try {
      await applicationsApi.transition(app.id, action);
      load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <Link to="/review" className="text-sm text-navy-600 mb-4 inline-block">
        ← All postings
      </Link>
      <h1 className="font-display text-3xl font-semibold text-navy-900 mb-1">
        {posting?.title || "…"}
      </h1>
      <p className="text-ink/50 mb-6">
        {applications.length} applicant{applications.length === 1 ? "" : "s"} shown
      </p>

      <div className="flex gap-2 mb-4 flex-wrap">
        {["", "submitted", "under_review", "shortlisted", "admitted", "documents_required", "rejected", "withdrawn"].map(
          (s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`text-xs px-3 py-1 rounded-full border ${
                statusFilter === s
                  ? "bg-navy-700 text-white border-navy-700"
                  : "border-navy-100 text-ink/50"
              }`}
            >
              {s === "" ? "All" : s.replaceAll("_", " ")}
            </button>
          )
        )}
      </div>

      {loading ? (
        <p className="text-ink/40">Loading…</p>
      ) : applications.length === 0 ? (
        <p className="text-ink/40">No applicants in this status.</p>
      ) : (
        <div className="grid gap-3">
          {applications.map((app) => (
            <div
              key={app.id}
              className="bg-paper-raised border border-navy-100 rounded-xl p-4"
            >
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <div className="font-medium text-navy-900">
                    {app.student.first_name} {app.student.last_name}{" "}
                    <span className="text-ink/40 font-normal">@{app.student.username}</span>
                  </div>
                  <div className="text-sm text-ink/50">{app.student.email}</div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusPill status={app.status} />
                  {app.available_actions.map((action) => (
                    <button
                      key={action}
                      disabled={busyId === app.id}
                      onClick={() => handleAction(app, action)}
                      className={`text-sm px-3 py-1.5 rounded-full disabled:opacity-50 ${ACTION_META[action]?.classes}`}
                    >
                      {ACTION_META[action]?.label || action}
                    </button>
                  ))}
                </div>
              </div>
              {app.cover_note && (
                <p className="text-sm text-ink/60 mt-2 border-t border-navy-100 pt-2">
                  {app.cover_note}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
