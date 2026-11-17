// Small presentational pieces shared by the Campaigns pages

const CAMPAIGN_STATUS = {
  draft:     ["Draft",     "bg-gray-100 text-gray-700 border-gray-200",         "bg-gray-500/20 text-gray-300 border-gray-500/30"],
  running:   ["Running",   "bg-emerald-50 text-emerald-700 border-emerald-200", "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"],
  paused:    ["Paused",    "bg-amber-50 text-amber-700 border-amber-200",       "bg-amber-500/20 text-amber-300 border-amber-500/30"],
  completed: ["Completed", "bg-blue-50 text-blue-700 border-blue-200",          "bg-blue-500/20 text-blue-300 border-blue-500/30"],
};

const RECIPIENT_STATUS = {
  new:       ["Not written",  "bg-gray-100 text-gray-600 border-gray-200",         "bg-gray-500/20 text-gray-300 border-gray-500/30"],
  queued:    ["Writing...",   "bg-indigo-50 text-indigo-700 border-indigo-200",    "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"],
  ready:     ["Ready",        "bg-blue-50 text-blue-700 border-blue-200",          "bg-blue-500/20 text-blue-300 border-blue-500/30"],
  scheduled: ["Scheduled",    "bg-purple-50 text-purple-700 border-purple-200",    "bg-purple-500/20 text-purple-300 border-purple-500/30"],
  contacted: ["Contacted",    "bg-emerald-50 text-emerald-700 border-emerald-200", "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"],
  completed: ["Sequence done", "bg-gray-100 text-gray-700 border-gray-200",        "bg-gray-500/20 text-gray-300 border-gray-500/30"],
  replied:   ["Replied",      "bg-green-100 text-green-800 border-green-300",      "bg-green-500/25 text-green-300 border-green-500/40"],
  failed:    ["Send failed",  "bg-red-50 text-red-600 border-red-200",             "bg-red-500/20 text-red-300 border-red-500/30"],
  error:     ["Write failed", "bg-red-50 text-red-600 border-red-200",             "bg-red-500/20 text-red-300 border-red-500/30"],
  unsubscribed: ["Unsubscribed", "bg-gray-100 text-gray-500 border-gray-200 line-through", "bg-gray-500/20 text-gray-400 border-gray-500/30 line-through"],
};

function Badge({ map, status, darkMode }) {
  const [label, light, dark] = map[status] || [status, map.draft?.[1] || "", map.draft?.[2] || ""];
  return (
    <span className={`px-3 py-1 rounded-full border text-xs font-medium whitespace-nowrap ${darkMode ? dark : light}`}>{label}</span>
  );
}

export function CampaignStatusBadge({ status, darkMode }) {
  return <Badge map={CAMPAIGN_STATUS} status={status} darkMode={darkMode} />;
}

export function RecipientStatusBadge({ status, darkMode }) {
  return <Badge map={RECIPIENT_STATUS} status={status} darkMode={darkMode} />;
}
