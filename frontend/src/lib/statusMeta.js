export const STATUS_META = {
  submitted: { label: "Submitted", classes: "bg-navy-50 text-navy-700" },
  under_review: { label: "Under review", classes: "bg-navy-100 text-navy-700" },
  shortlisted: { label: "Shortlisted", classes: "bg-amber-100 text-amber-600" },
  admitted: { label: "Admitted", classes: "bg-moss-100 text-moss-600" },
  documents_required: { label: "Documents required", classes: "bg-amber-100 text-amber-600" },
  consent_pending: { label: "Consent pending", classes: "bg-amber-100 text-amber-600" },
  documents_shared: { label: "Documents shared", classes: "bg-moss-100 text-moss-600" },
  rejected: { label: "Not selected", classes: "bg-rust-100 text-rust-600" },
  withdrawn: { label: "Withdrawn", classes: "bg-ink/5 text-ink/60" },
};

export const ACTION_META = {
  start_review: { label: "Start review", classes: "bg-navy-600 hover:bg-navy-700 text-white" },
  shortlist: { label: "Shortlist", classes: "bg-amber-500 hover:bg-amber-600 text-white" },
  admit: { label: "Admit", classes: "bg-moss-500 hover:bg-moss-600 text-white" },
  reject: { label: "Reject", classes: "bg-rust-500 hover:bg-rust-600 text-white" },
  withdraw: { label: "Withdraw", classes: "bg-ink/10 hover:bg-ink/20 text-ink" },
};
