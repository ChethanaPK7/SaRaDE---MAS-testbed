import { useEffect, useMemo, useState } from "react";
import { agentsApi, postingsApi } from "../api/resources";

function Card({ title, children }) {
  return <section className="bg-paper-raised border border-navy-100 rounded-2xl p-6 shadow-sm"><h2 className="font-display text-xl font-semibold text-navy-900">{title}</h2>{children}</section>;
}

const tabs = [
  ["profile", "Profile"], ["match", "Matcher"], ["map", "Learning Map"],
  ["sop", "SOP"], ["verify", "Verify"], ["coordinate", "Coordinator"],
];

export default function AgentsPage() {
  const [tab, setTab] = useState("profile");
  const [profileText, setProfileText] = useState("");
  const [profile, setProfile] = useState(null);
  const [parserResult, setParserResult] = useState(null);
  const [matches, setMatches] = useState([]);
  const [postings, setPostings] = useState([]);
  const [selectedPosting, setSelectedPosting] = useState("");
  const [constraints, setConstraints] = useState("");
  const [learningMap, setLearningMap] = useState(null);
  const [sop, setSop] = useState(null);
  const [verification, setVerification] = useState(null);
  const [plan, setPlan] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { postingsApi.list({ open_only: true }).then((d) => setPostings(d.results || d)).catch(() => {}); }, []);
  const profileJson = useMemo(() => profile ? JSON.stringify(profile, null, 2) : "", [profile]);
  const fail = (e) => setError(e?.response?.data?.detail || "The agent could not complete the request.");
  const selected = postings.find((p) => String(p.id) === String(selectedPosting));

  async function run(fn) { setError(""); setLoading(true); try { await fn(); } catch (e) { fail(e); } finally { setLoading(false); } }
  async function parse() { await run(async () => { const r = await agentsApi.parseProfile(profileText); setParserResult(r); setProfile(r); }); }
  async function match() { if (!profile) return setError("Parse a profile first."); await run(async () => setMatches((await agentsApi.matchOpportunities(profile, 8)).matches || [])); }
  async function map() { if (!profile || !selectedPosting) return setError("Provide a profile and select an opportunity."); await run(async () => setLearningMap(await agentsApi.learningMap(profile, selectedPosting))); }
  async function writeSop() { if (!profile || !selectedPosting) return setError("Provide a profile and select an opportunity."); await run(async () => setSop(await agentsApi.writeSop(profile, selectedPosting, constraints))); }
  async function verify() { if (!profile || (!sop && !learningMap && !matches.length)) return setError("Generate an agent result first."); await run(async () => setVerification(await agentsApi.verify(profile, { matches, learning_map: learningMap, sop }))); }
  async function coordinate() { if (!profile) return setError("Parse a profile first."); await run(async () => setPlan(await agentsApi.coordinationPlan({ profile, matches, learning_map: learningMap, sop, consent_scope: { purpose: "research-development" } }))); }
  async function orchestrate() {
    if (!profile || !selectedPosting) return setError("Provide a profile and select an opportunity.");
    await run(async () => setWorkflow(await agentsApi.orchestrate({ profile, posting_id: selectedPosting, matches, learning_map: learningMap, sop, constraints, consent_scope: { purpose: "research-development" }, verify: true })));
  }

  return <div className="space-y-6">
    <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-600">SaRaDE agent environment</p><h1 className="font-display text-3xl font-semibold text-navy-900 mt-1">Research Ecosystem Agents</h1><p className="text-ink/55 mt-1 max-w-4xl">A coordinated environment for profile analysis, opportunity discovery, skill development, application preparation, verification, and learned agent orchestration. Agents receive only data explicitly supplied to them.</p></div>
    <div className="flex gap-2 flex-wrap">{tabs.map(([id, label]) => <button key={id} onClick={() => setTab(id)} className={`px-4 py-2 rounded-full text-sm font-medium ${tab === id ? "bg-navy-700 text-white" : "bg-navy-50 text-navy-700"}`}>{label}</button>)}</div>
    {error && <div className="rounded-lg bg-rust-100 text-rust-600 px-4 py-3 text-sm">{error}</div>}

    {(tab === "map" || tab === "sop" || tab === "coordinate") && <Card title="Target opportunity"><select className="mt-4 w-full rounded-xl border border-navy-100 px-3 py-2.5 bg-white" value={selectedPosting} onChange={(e) => setSelectedPosting(e.target.value)}><option value="">Select an open opportunity…</option>{postings.map((p) => <option key={p.id} value={p.id}>{p.title} — {p.institution?.name || p.institution}</option>)}</select>{selected && <p className="text-xs text-ink/45 mt-2">{selected.lab || "Research opportunity"}</p>}</Card>}

    {tab === "profile" && <Card title="AI Profile Parser"><p className="text-sm text-ink/55 mt-1">Extract only explicit facts from a CV or academic profile.</p><textarea className="w-full min-h-64 mt-4 rounded-xl border border-navy-100 p-4 bg-white" placeholder="Paste CV or research profile text…" value={profileText} onChange={(e) => setProfileText(e.target.value)} /><button disabled={loading} onClick={parse} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Parsing…" : "Parse profile"}</button>{parserResult && <pre className="mt-5 rounded-xl bg-navy-900 text-white p-4 overflow-auto text-xs">{JSON.stringify(parserResult, null, 2)}</pre>}</Card>}

    {tab === "match" && <Card title="Opportunity Matcher"><p className="text-sm text-ink/55 mt-1">Technical compatibility estimate against currently open opportunities.</p>{profile ? <pre className="mt-4 rounded-xl bg-navy-50 p-4 overflow-auto text-xs max-h-56">{profileJson}</pre> : <p className="mt-4 text-sm text-ink/45">Parse a profile first.</p>}<button disabled={loading || !profile} onClick={match} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Matching…" : "Find opportunities"}</button><div className="grid gap-3 mt-5">{matches.map((m) => <div key={m.posting_id} className="border border-navy-100 rounded-xl p-4"><div className="flex justify-between gap-3"><h3 className="font-semibold text-navy-900">{m.title}</h3><span className="text-sm font-semibold text-amber-600">{m.score}/100</span></div><p className="text-sm text-ink/60 mt-2">{(m.reasons || []).join(" · ")}</p>{m.gaps?.length > 0 && <p className="text-xs text-ink/45 mt-2">Gaps: {m.gaps.join(" · ")}</p>}</div>)}</div></Card>}

    {tab === "map" && <Card title="Learning Map Agent"><p className="text-sm text-ink/55 mt-1">Turn the current profile and target into an explicit, evidence-oriented development pathway.</p><button disabled={loading || !profile || !selectedPosting} onClick={map} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Building…" : "Build learning map"}</button>{learningMap && <pre className="mt-5 rounded-xl bg-navy-900 text-white p-4 overflow-auto text-xs">{JSON.stringify(learningMap, null, 2)}</pre>}</Card>}

    {tab === "sop" && <Card title="Student SOP Writer"><p className="text-sm text-ink/55 mt-1">Generate a research-specific first draft without inventing achievements.</p><textarea className="w-full min-h-28 mt-4 rounded-xl border border-navy-100 p-4 bg-white" placeholder="Optional constraints or instructions…" value={constraints} onChange={(e) => setConstraints(e.target.value)} /><button disabled={loading || !profile || !selectedPosting} onClick={writeSop} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Writing…" : "Draft SOP"}</button>{sop && <div className="mt-5 border border-navy-100 rounded-xl p-5"><h3 className="font-display text-xl font-semibold text-navy-900">{sop.title}</h3><p className="whitespace-pre-wrap text-sm leading-7 mt-3 text-ink/80">{sop.draft}</p>{sop.notes && <p className="text-xs text-ink/45 mt-4">{sop.notes}</p>}</div>}</Card>}

    {tab === "verify" && <Card title="Verification Agent"><p className="text-sm text-ink/55 mt-1">Audit generated outputs for unsupported claims, contradictions, and avoidable data exposure.</p><button disabled={loading || !profile} onClick={verify} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Auditing…" : "Verify current outputs"}</button>{verification && <pre className="mt-5 rounded-xl bg-navy-900 text-white p-4 overflow-auto text-xs">{JSON.stringify(verification, null, 2)}</pre>}</Card>}

    {tab === "coordinate" && <Card title="QMIX Coordinator"><p className="text-sm text-ink/55 mt-1">Centralized-training/decentralized-execution coordinator chooses which specialized agents should contribute. The research implementation uses QMIX; if its checkpoint is unavailable, a transparent fallback policy is used.</p><button disabled={loading || !profile} onClick={coordinate} className="mt-4 rounded-full bg-navy-700 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Planning…" : "Plan agent actions"}</button>{plan && <pre className="mt-5 rounded-xl bg-navy-900 text-white p-4 overflow-auto text-xs">{JSON.stringify(plan, null, 2)}</pre>}<div className="mt-6 border-t border-navy-100 pt-5"><h3 className="font-semibold text-navy-900">Run coordinated workflow</h3><p className="text-sm text-ink/55 mt-1">Uses the selected plan to invoke relevant agents and then runs verification.</p><button disabled={loading || !profile || !selectedPosting} onClick={orchestrate} className="mt-4 rounded-full bg-amber-500 text-white px-5 py-2.5 text-sm font-medium disabled:opacity-50">{loading ? "Running…" : "Run workflow"}</button>{workflow && <pre className="mt-5 rounded-xl bg-navy-900 text-white p-4 overflow-auto text-xs max-h-[32rem]">{JSON.stringify(workflow, null, 2)}</pre>}</div></Card>}
  </div>;
}
