import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { authApi } from "../api/resources";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [institutions, setInstitutions] = useState([]);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    role: "student",
    institution_id: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authApi.institutions().then((data) => setInstitutions(data.results || data));
  }, []);

  const needsInstitution = form.role !== "student";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = { ...form };
      if (!needsInstitution) delete payload.institution_id;
      else payload.institution_id = Number(payload.institution_id);
      await register(payload);
      navigate("/postings");
    } catch (err) {
      const data = err?.response?.data;
      setError(
        data ? Object.values(data).flat().join(" ") : "Could not create account."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-8">
      <h1 className="font-display text-2xl font-semibold text-navy-900 mb-6">
        Create an account
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1">First name</label>
            <input
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1">Last name</label>
            <input
              className="w-full rounded-lg border border-navy-100 px-3 py-2"
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">Username</label>
          <input
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">Email</label>
          <input
            type="email"
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">Password</label>
          <input
            type="password"
            className="w-full rounded-lg border border-navy-100 px-3 py-2"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">I am a…</label>
          <select
            className="w-full rounded-lg border border-navy-100 px-3 py-2 bg-white"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            <option value="student">Student</option>
            <option value="faculty">Faculty</option>
            <option value="institution_admin">Institution admin</option>
          </select>
        </div>
        {needsInstitution && (
          <div>
            <label className="block text-sm font-medium text-ink/70 mb-1">Institution</label>
            <select
              className="w-full rounded-lg border border-navy-100 px-3 py-2 bg-white"
              value={form.institution_id}
              onChange={(e) => setForm({ ...form, institution_id: e.target.value })}
              required
            >
              <option value="" disabled>
                Select…
              </option>
              {institutions.map((inst) => (
                <option key={inst.id} value={inst.id}>
                  {inst.name}
                </option>
              ))}
            </select>
          </div>
        )}
        {error && <p className="text-sm text-rust-600">{error}</p>}
        <button
          disabled={busy}
          className="w-full bg-navy-700 hover:bg-navy-600 text-white font-medium rounded-lg py-2 transition-colors disabled:opacity-60"
        >
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-ink/50 mt-4">
        Already have an account?{" "}
        <Link to="/login" className="text-navy-600 font-medium">
          Log in
        </Link>
      </p>
    </div>
  );
}
