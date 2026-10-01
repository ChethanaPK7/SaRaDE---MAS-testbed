import { useEffect, useState } from "react";
import { notificationsApi } from "../api/resources";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    notificationsApi.list().then((data) => setNotifications(data.results || data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function markAllRead() {
    await notificationsApi.markAllRead();
    load();
  }

  return (
    <div className="max-w-xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-3xl font-semibold text-navy-900">Notifications</h1>
        {notifications.some((n) => !n.is_read) && (
          <button onClick={markAllRead} className="text-sm text-navy-600 font-medium">
            Mark all read
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-ink/40">Loading…</p>
      ) : notifications.length === 0 ? (
        <p className="text-ink/40">Nothing yet.</p>
      ) : (
        <div className="grid gap-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`rounded-lg px-4 py-3 border ${
                n.is_read
                  ? "border-navy-100 bg-paper-raised text-ink/60"
                  : "border-amber-400 bg-amber-100/40 text-ink"
              }`}
            >
              <p className="text-sm">{n.message}</p>
              <p className="text-xs text-ink/40 mt-1">
                {new Date(n.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
