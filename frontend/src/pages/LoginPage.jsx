import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(form.username, form.password);
      navigate("/postings");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-12">
      <h1 className="font-display text-2xl font-semibold text-navy-900 mb-1">Log in</h1>
      <p className="text-sm text-ink/50 mb-6">
        Try <code className="text-navy-600">faculty_demo</code> or{" "}
        <code className="text-navy-600">student_demo_001</code>, password{" "}
        <code className="text-navy-600">demo1234</code>, after running the seed command.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">Username</label>
          <input
            className="w-full rounded-lg border border-navy-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-navy-400"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink/70 mb-1">Password</label>
          <input
            type="password"
            className="w-full rounded-lg border border-navy-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-navy-400"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        {error && <p className="text-sm text-rust-600">{error}</p>}
        <button
          disabled={busy}
          className="w-full bg-navy-700 hover:bg-navy-600 text-white font-medium rounded-lg py-2 transition-colors disabled:opacity-60"
        >
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="text-sm text-ink/50 mt-4">
        No account?{" "}
        <Link to="/register" className="text-navy-600 font-medium">
          Sign up
        </Link>
      </p>
    </div>
  );
}
