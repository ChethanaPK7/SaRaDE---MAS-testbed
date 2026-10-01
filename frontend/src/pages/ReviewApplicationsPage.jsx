import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { postingsApi } from "../api/resources";

export default function ReviewApplicationsPage() {
  const { user } = useAuth();
  const [postings, setPostings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    postingsApi
      .mine(user.institution?.id)
      .then((data) => setPostings(data.results || data))
      .finally(() => setLoading(false));
  }, [user]);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold text-navy-900 mb-1">
        Review applications
      </h1>
      <p className="text-ink/50 mb-6">
        Postings from {user.institution?.name}. Open one to shortlist, admit, or reject applicants.
      </p>

      {loading ? (
        <p className="text-ink/40">Loading…</p>
      ) : postings.length === 0 ? (
        <p className="text-ink/40">
          No postings yet.{" "}
          <Link to="/postings/new" className="text-navy-600 font-medium">
            Create one
          </Link>
          .
        </p>
      ) : (
        <div className="grid gap-3">
          {postings.map((p) => (
            <Link
              key={p.id}
              to={`/review/${p.id}`}
              className="block bg-paper-raised border border-navy-100 rounded-xl p-4 hover:border-navy-400 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="font-display font-semibold text-navy-900">{p.title}</span>
                <span className="text-sm text-ink/50">
                  {p.application_count} applicant{p.application_count === 1 ? "" : "s"}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
