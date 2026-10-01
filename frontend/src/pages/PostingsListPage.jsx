import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { postingsApi } from "../api/resources";

export default function PostingsListPage() {
  const [postings, setPostings] = useState([]);
  const [search, setSearch] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = { open_only: openOnly };
    if (search) params.search = search;
    postingsApi
      .list(params)
      .then((data) => setPostings(data.results || data))
      .finally(() => setLoading(false));
  }, [search, openOnly]);

  return (
    <div>
      <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-navy-900">
            Internship postings
          </h1>
          <p className="text-ink/50 mt-1">Search across every lab and institution on SRIP.</p>
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <input
          placeholder="Search by title, lab, or keyword…"
          className="flex-1 rounded-lg border border-navy-100 px-3 py-2 bg-white"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-ink/60 whitespace-nowrap">
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(e) => setOpenOnly(e.target.checked)}
          />
          Open only
        </label>
      </div>

      {loading ? (
        <p className="text-ink/40">Loading…</p>
      ) : postings.length === 0 ? (
        <p className="text-ink/40">No postings match your search.</p>
      ) : (
        <div className="grid gap-4">
          {postings.map((p) => (
            <Link
              key={p.id}
              to={`/postings/${p.id}`}
              className="block bg-paper-raised border border-navy-100 rounded-xl p-5 hover:border-navy-400 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-lg font-semibold text-navy-900">
                    {p.title}
                  </h2>
                  <p className="text-sm text-ink/50 mt-0.5">
                    {p.institution?.name}
                    {p.lab && ` · ${p.lab}`}
                  </p>
                </div>
                {!p.is_open && (
                  <span className="status-pill bg-ink/10 text-ink/50 shrink-0">Closed</span>
                )}
              </div>
              <div className="flex gap-5 mt-3 text-sm text-ink/60">
                <span>{p.duration_weeks} weeks</span>
                <span>₹{p.stipend?.toLocaleString("en-IN")}/mo</span>
                <span>Deadline {p.application_deadline}</span>
                <span>{p.application_count} applicant{p.application_count === 1 ? "" : "s"}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
