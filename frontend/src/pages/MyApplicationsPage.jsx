import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { applicationsApi } from "../api/resources";
import StatusPill from "../components/StatusPill";
import { ACTION_META } from "../lib/statusMeta";

export default function MyApplicationsPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    applicationsApi.list().then((data) => setApplications(data.results || data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleWithdraw(app) {
    if (!confirm(`Withdraw your application to "${app.posting.title}"?`)) return;
    await applicationsApi.transition(app.id, "withdraw");
    load();
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold text-navy-900 mb-6">
        My applications
      </h1>

      {loading ? (
        <p className="text-ink/40">Loading…</p>
      ) : applications.length === 0 ? (
        <p className="text-ink/40">
          You haven't applied to anything yet.{" "}
          <Link to="/postings" className="text-navy-600 font-medium">
            Browse postings
          </Link>
          .
        </p>
      ) : (
        <div className="grid gap-3">
          {applications.map((app) => (
            <div
              key={app.id}
              className="bg-paper-raised border border-navy-100 rounded-xl p-4 flex items-center justify-between gap-4"
            >
              <div>
                <Link
                  to={`/postings/${app.posting.id}`}
                  className="font-display font-semibold text-navy-900"
                >
                  {app.posting.title}
                </Link>
                <p className="text-sm text-ink/50">{app.posting.institution?.name}</p>
              </div>
              <div className="flex items-center gap-3">
                <StatusPill status={app.status} />
                {app.available_actions.includes("withdraw") && (
                  <button
                    onClick={() => handleWithdraw(app)}
                    className={`text-sm px-3 py-1.5 rounded-full ${ACTION_META.withdraw.classes}`}
                  >
                    Withdraw
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
