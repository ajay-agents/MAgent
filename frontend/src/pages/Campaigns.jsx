import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";
import { FiPlus, FiUsers, FiSend, FiCornerUpLeft, FiX, FiLayers } from "react-icons/fi";
import { CampaignStatusBadge } from "../components/CampaignBits";

const PURPOSES = [
  ["cold_outreach", "Cold Outreach"], ["networking", "Networking"], ["follow_up", "Follow-Up"],
  ["job_application", "Job Application"], ["partnership", "Partnership"], ["thank_you", "Thank You"],
];
const TONES   = ["professional", "friendly", "formal", "casual", "persuasive"];
const LENGTHS = ["short", "medium", "long"];

export default function Campaigns() {
  const { darkMode } = useTheme();
  const navigate = useNavigate();

  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    api.get("/api/campaigns").then(setItems).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-extrabold flex items-center gap-3"><FiLayers /> Campaigns</h1>
              <p className="mt-2 text-gray-500">Send a personalised email to a whole list, with automatic follow-ups.</p>
            </div>
            <button onClick={() => setShowNew(true)}
              className={`px-5 py-3 rounded-xl text-white flex items-center gap-2 shadow-lg transition hover:scale-[1.02] ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600 shadow-purple-500/30" : "bg-gray-900 hover:bg-black"}`}>
              <FiPlus /> New Campaign
            </button>
          </div>

          {loading && <p className="text-gray-500">Loading...</p>}

          {!loading && items.length === 0 && (
            <div className={`rounded-3xl p-12 text-center border shadow-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
              <FiLayers size={55} className="mx-auto mb-5 text-gray-400" />
              <h2 className="text-2xl font-bold">No campaigns yet</h2>
              <p className="mt-3 text-gray-500">Upload a CSV of contacts and MailFlow writes a personalised email for each one.</p>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-6">
            {items.map((c) => (
              <button key={c.id} onClick={() => navigate(`/campaigns/${c.id}`)}
                className={`text-left rounded-3xl p-6 shadow-xl border transition ${darkMode ? "bg-[#11141D] border-gray-800 hover:bg-[#151923]" : "bg-white border-gray-200 hover:bg-gray-50"}`}>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <h2 className="text-xl font-bold">{c.name}</h2>
                    <p className="text-sm text-gray-500 mt-1 capitalize">{c.purpose.replace(/_/g, " ")} · {c.tone}</p>
                  </div>
                  <CampaignStatusBadge status={c.status} darkMode={darkMode} />
                </div>
                <div className="mt-5 grid grid-cols-3 gap-4">
                  <Stat icon={<FiUsers />} label="Recipients" value={c.stats.recipients} />
                  <Stat icon={<FiSend />} label="Emails sent" value={c.stats.emails_sent} />
                  <Stat icon={<FiCornerUpLeft />} label="Replied" value={c.stats.replied} />
                </div>
              </button>
            ))}
          </div>
        </main>
      </div>

      {showNew && <NewCampaignModal darkMode={darkMode} onClose={() => setShowNew(false)}
        onCreated={(c) => navigate(`/campaigns/${c.id}`)} />}
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500 flex items-center gap-1.5">{icon} {label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function NewCampaignModal({ darkMode, onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", purpose: "cold_outreach", tone: "professional", length: "medium", sender_name: "", context: "" });
  const [error, setError]   = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/api/profile")
      .then((p) => p.full_name && setForm((f) => (f.sender_name ? f : { ...f, sender_name: p.full_name })))
      .catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const field = `w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-500 focus:border-indigo-500" : "bg-white border-gray-200 focus:border-gray-900"}`;

  const create = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      onCreated(await api.post("/api/campaigns", { ...form, context: form.context || null }));
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <form onSubmit={create} className={`w-[560px] max-h-[90vh] overflow-y-auto rounded-3xl p-6 shadow-2xl ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-2xl font-bold">New Campaign</h2>
          <button type="button" onClick={onClose}><FiX size={24} /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-500 block mb-1">Campaign name</label>
            <input required maxLength={150} value={form.name} onChange={set("name")} placeholder="e.g. Coaching institutes, Indore" className={field} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-sm text-gray-500 block mb-1">Purpose</label>
              <select value={form.purpose} onChange={set("purpose")} className={field}>
                {PURPOSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-500 block mb-1">Tone</label>
              <select value={form.tone} onChange={set("tone")} className={`${field} capitalize`}>
                {TONES.map((t) => <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-500 block mb-1">Length</label>
              <select value={form.length} onChange={set("length")} className={field}>
                {LENGTHS.map((l) => <option key={l} value={l}>{l[0].toUpperCase() + l.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm text-gray-500 block mb-1">Your name</label>
            <input required maxLength={100} value={form.sender_name} onChange={set("sender_name")} className={field} />
          </div>
          <div>
            <label className="text-sm text-gray-500 block mb-1">What's this campaign about? <span className="text-xs">(shared by every email)</span></label>
            <textarea rows={4} maxLength={2000} value={form.context} onChange={set("context")} className={`${field} resize-y`}
              placeholder="e.g. Offering a free 2-week pilot of our AI study assistant for their students before the board exams." />
          </div>
        </div>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
        <button type="submit" disabled={saving}
          className={`mt-6 w-full py-3 rounded-xl text-white font-medium disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
          {saving ? "Creating..." : "Create & add recipients"}
        </button>
      </form>
    </div>
  );
}
