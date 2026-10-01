import { STATUS_META } from "../lib/statusMeta";

export default function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: status, classes: "bg-ink/10 text-ink" };
  return <span className={`status-pill ${meta.classes}`}>{meta.label}</span>;
}
