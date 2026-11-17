import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";
import UpgradeModal from "../components/UpgradeModal";
import { FiCalendar, FiSend, FiSave, FiCopy, FiCheckCircle, FiX, FiRefreshCw } from "react-icons/fi";
import { HiSparkles } from "react-icons/hi2";

const REFINEMENTS = [
  { key: "shorter",     label: "Shorter" },
  { key: "longer",      label: "Longer" },
  { key: "warmer",      label: "Warmer" },
  { key: "more_direct", label: "More direct" },
  { key: "more_formal", label: "More formal" },
];

const PURPOSE_MAP = {
  "Cold Outreach": "cold_outreach",
  "Networking":    "networking",
  "Follow-Up":     "follow_up",
  "Job-Application": "job_application",
  "Partnership":   "partnership",
  "Thank You":     "thank_you",
};

export default function CreateEmail() {
  const { darkMode } = useTheme();

  const selectFields = [
    { name: "purpose", label: "Purpose", options: ["Cold Outreach","Networking","Follow-Up","Job-Application","Partnership","Thank You"] },
    { name: "tone",    label: "Tone",    options: ["Professional","Friendly","Formal","Casual","Persuasive"] },
    { name: "length",  label: "Length",  options: ["Short","Medium","Long"] },
  ];

  const [formData, setFormData] = useState({
    purpose: "Cold Outreach", tone: "Professional", length: "Medium",
    sender: "", recipient: "", email: "", context: "",
  });

  const [loading, setLoading]               = useState(false);
  const [generatedEmail, setGeneratedEmail] = useState(null); // last saved server version { id, subject, body, ... }
  const [draft, setDraft]                   = useState({ subject: "", body: "" }); // what's in the editor
  const [busy, setBusy]                     = useState("");   // "" | "saving" | "regenerate" | refinement key | "custom"
  const [customInstruction, setCustomInstruction] = useState("");
  const [profileMissing, setProfileMissing] = useState(false);
  const [notification, setNotification]     = useState("");
  const [scheduleData, setScheduleData]     = useState({ date: "", time: "" });
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [error, setErrorText]               = useState("");
  const [modalError, setModalError]         = useState("");
  const [limitHit, setLimitHit]             = useState(false); // last error was a plan limit (402)
  const [showPlans, setShowPlans]           = useState(false);

  const setError = (msg) => { setErrorText(msg); setLimitHit(false); };
  const fail = (err, fallback) => {
    setErrorText(err.message || fallback);
    setLimitHit(err.status === 402);
  };

  const notify = (msg) => { setNotification(msg); setTimeout(() => setNotification(""), 3000); };

  const handleChange = (name, value) => setFormData((prev) => ({ ...prev, [name]: value }));

  // Prefill the sender from the saved profile
  useEffect(() => {
    api.get("/api/profile")
      .then((p) => {
        if (p.full_name) setFormData((prev) => (prev.sender ? prev : { ...prev, sender: p.full_name }));
        setProfileMissing(!p.full_name && !p.company && !p.about);
      })
      .catch(() => {});
  }, []);

  const showEmail = (email) => {
    setGeneratedEmail(email);
    setDraft({ subject: email.subject, body: email.body });
  };

  const dirty = !!generatedEmail && (draft.subject !== generatedEmail.subject || draft.body !== generatedEmail.body);

  const saveEdits = async () => {
    if (!dirty) return generatedEmail;
    if (!draft.subject.trim() || !draft.body.trim()) throw new Error("Subject and body can't be empty.");
    setBusy("saving");
    try {
      const saved = await api.patch(`/api/emails/${generatedEmail.id}`, { subject: draft.subject, body: draft.body });
      setGeneratedEmail(saved);
      return saved;
    } finally {
      setBusy("");
    }
  };

  const handleSave = async () => {
    setError("");
    try {
      await saveEdits();
      notify("Changes saved");
    } catch (err) {
      setError(err.message || "Saving failed.");
    }
  };

  // No refinement = a fresh take from the original inputs; otherwise rewrite the current (saved) draft
  const regenerate = async (refinement = null, instruction = null) => {
    if (!generatedEmail) return handleGenerate();
    const isFresh = !refinement && !instruction;
    if (isFresh && dirty && !window.confirm("Regenerating replaces your edits. Continue?")) return;
    setError("");
    try {
      if (!isFresh) await saveEdits(); // so the AI revises what the user actually sees
      setBusy(refinement || (instruction ? "custom" : "regenerate"));
      const result = await api.post(`/api/emails/${generatedEmail.id}/regenerate`, { refinement, instruction });
      showEmail(result);
      if (instruction) setCustomInstruction("");
      notify(isFresh ? "New version generated" : "Email refined");
    } catch (err) {
      fail(err, "Regeneration failed.");
    } finally {
      setBusy("");
    }
  };

  const handleGenerate = async () => {
    if (!formData.sender || !formData.recipient || !formData.email) {
      setError("Sender name, recipient name, and recipient email are required.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await api.post("/api/emails/generate", {
        purpose:         PURPOSE_MAP[formData.purpose] || "cold_outreach",
        tone:            formData.tone.toLowerCase(),
        length:          formData.length.toLowerCase(),
        sender_name:     formData.sender,
        recipient_name:  formData.recipient,
        recipient_email: formData.email,
        context:         formData.context || null,
      });
      showEmail(result); // { id, subject, body, ai_model, ... }
      notify("Email generated and saved as draft");
    } catch (err) {
      fail(err, "Generation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const copyEmail = () => {
    if (!generatedEmail) return;
    navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    notify("Email copied to clipboard");
  };

  const scheduleEmail = async () => {
    if (!generatedEmail) return;
    const scheduledAt = new Date(`${scheduleData.date}T${scheduleData.time}:00`).toISOString();
    try {
      await saveEdits();
      await api.post(`/api/emails/${generatedEmail.id}/schedule`, { scheduled_at: scheduledAt });
      notify("Email scheduled successfully");
      setShowScheduleModal(false);
    } catch (err) {
      setError(err.message || "Scheduling failed.");
    }
  };

  const [sending, setSending] = useState(false);

  const sendNow = async () => {
    if (!generatedEmail) return;
    setSending(true);
    setError("");
    try {
      await saveEdits();
      await api.post(`/api/emails/${generatedEmail.id}/send`, {});
      notify("Email sent successfully!");
    } catch (err) {
      setError(err.message || "Send failed. Check your Gmail credentials in Settings.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 flex flex-col p-6 min-h-0">
          {notification && (
            <div className={`mb-3 px-5 py-3 rounded-xl w-fit flex items-center gap-2 ${darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>
              <FiCheckCircle /> {notification}
            </div>
          )}
          {error && (
            <div className="mb-3 px-5 py-3 rounded-xl w-fit flex items-center gap-3 bg-red-500/10 text-red-400 border border-red-400/30">
              {error}
              {limitHit && (
                <button onClick={() => setShowPlans(true)} className={`shrink-0 px-3 py-1 rounded-lg text-sm text-white ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
                  See plans
                </button>
              )}
            </div>
          )}

          <div className={`flex-1 min-h-0 flex rounded-3xl overflow-hidden shadow-2xl border backdrop-blur-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white/70 border-gray-200"}`}>
            {/* LEFT */}
            <div className={`w-1/2 p-10 overflow-y-auto ${darkMode ? "bg-[#11141D]" : "bg-white/70"}`}>
              <h1 className={`text-4xl font-extrabold ${darkMode ? "text-white" : "text-gray-900"}`}>AI Email Builder</h1>
              <p className={`mt-2 mb-8 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Create personalized emails with AI in seconds.</p>

              <div className="grid grid-cols-3 gap-4">
                {selectFields.map((field) => (
                  <div key={field.name} className="flex flex-col gap-2">
                    <label className={`text-sm font-medium ${darkMode ? "text-gray-300" : "text-gray-700"}`}>{field.label}</label>
                    <select value={formData[field.name]} onChange={(e) => handleChange(field.name, e.target.value)}
                      className={`p-3.5 rounded-xl border outline-none transition-all duration-300 cursor-pointer appearance-none shadow-sm ${darkMode ? "bg-[#090B12] border-gray-700 text-white hover:border-indigo-500 focus:border-indigo-500" : "bg-white border-gray-200 text-gray-900 focus:border-gray-900"}`}>
                      {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4 mt-6">
                {[
                  { name: "sender",    placeholder: "Your Name" },
                  { name: "recipient", placeholder: "Recipient Name" },
                  { name: "email",     placeholder: "Recipient Email" },
                ].map((f) => (
                  <input key={f.name} value={formData[f.name]} onChange={(e) => handleChange(f.name, e.target.value)}
                    placeholder={f.placeholder}
                    className={`p-3 rounded-xl border outline-none transition ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-500" : "bg-white border-gray-200"}`} />
                ))}
              </div>

              {profileMissing && (
                <p className={`mt-3 text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                  Tip: <Link to="/settings" className={`underline ${darkMode ? "text-indigo-300" : "text-gray-900"}`}>add your sender profile</Link> so every email knows who you are and what you offer.
                </p>
              )}

              <textarea rows={6} value={formData.context} onChange={(e) => handleChange("context", e.target.value)}
                placeholder="Write context for AI (e.g. how you know them, what you want to achieve)..."
                className={`w-full mt-6 p-4 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-500" : "bg-white border-gray-200"}`} />

              <button onClick={handleGenerate} disabled={loading}
                className={`mt-6 w-full py-4 rounded-xl flex items-center justify-center gap-2 text-white transition hover:scale-[1.02] shadow-lg disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 shadow-purple-500/30" : "bg-gray-900 hover:bg-black"}`}>
                <HiSparkles />
                {loading ? "Generating..." : "Generate Email"}
              </button>
            </div>

            {/* RIGHT */}
            <div className={`w-1/2 flex flex-col ${darkMode ? "bg-[#090B12]" : "bg-gray-50"}`}>
              <div className={`border-b px-8 py-5 flex justify-between items-center ${darkMode ? "border-gray-800 bg-[#11141D]" : "bg-white"}`}>
                <div>
                  <h2 className="text-xl font-bold">Email Preview</h2>
                  {generatedEmail && <p className="text-xs text-gray-500 mt-0.5">Model: {generatedEmail.ai_model} · ${generatedEmail.estimated_cost_usd?.toFixed(5)}</p>}
                </div>
                <button onClick={() => regenerate()} disabled={loading || !!busy}
                  className={`px-4 py-2 rounded-xl border flex items-center gap-2 disabled:opacity-50 ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                  <FiRefreshCw className={busy === "regenerate" ? "animate-spin" : ""} />
                  {busy === "regenerate" ? "Regenerating..." : "Regenerate"}
                </button>
              </div>

              {generatedEmail && (
                <div className={`border-b px-8 py-3 ${darkMode ? "border-gray-800 bg-[#11141D]" : "bg-white"}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-gray-500 mr-1">Refine:</span>
                    {REFINEMENTS.map((r) => (
                      <button key={r.key} onClick={() => regenerate(r.key)} disabled={!!busy}
                        className={`px-3 py-1.5 rounded-full border text-sm transition disabled:opacity-50 ${
                          busy === r.key
                            ? darkMode ? "border-indigo-500 text-indigo-300" : "border-gray-900 text-gray-900"
                            : darkMode ? "border-gray-700 text-gray-300 hover:border-indigo-500 hover:text-white" : "border-gray-200 text-gray-600 hover:border-gray-900 hover:text-gray-900"
                        }`}>
                        {busy === r.key ? "Refining..." : r.label}
                      </button>
                    ))}
                  </div>
                  <form onSubmit={(e) => { e.preventDefault(); if (customInstruction.trim()) regenerate(null, customInstruction.trim()); }}
                    className="mt-2 flex gap-2">
                    <input value={customInstruction} onChange={(e) => setCustomInstruction(e.target.value)} maxLength={500}
                      placeholder='Or tell the AI what to change, e.g. "mention our free trial"'
                      className={`flex-1 px-3 py-2 rounded-lg border text-sm outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-500 focus:border-indigo-500" : "bg-white border-gray-200 focus:border-gray-900"}`} />
                    <button type="submit" disabled={!!busy || !customInstruction.trim()}
                      className={`px-4 py-2 rounded-lg text-sm text-white disabled:opacity-50 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
                      {busy === "custom" ? "Applying..." : "Apply"}
                    </button>
                  </form>
                </div>
              )}

              <div className="flex-1 p-8 overflow-y-auto">
                <div className={`rounded-2xl shadow-lg p-6 space-y-5 border ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
                  {generatedEmail ? (
                    <>
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                          <p className="text-xs text-gray-500 mb-1">Subject</p>
                          <input value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} maxLength={300}
                            className={`w-full font-semibold bg-transparent outline-none rounded-lg px-2 py-1 -mx-2 border border-transparent transition ${darkMode ? "hover:border-gray-700 focus:border-indigo-500" : "hover:border-gray-200 focus:border-gray-900"}`} />
                        </div>
                        <button onClick={copyEmail} className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                          <FiCopy /> Copy
                        </button>
                      </div>
                      <hr className={darkMode ? "border-gray-800" : "border-gray-200"} />
                      <textarea value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} rows={14}
                        className={`w-full bg-transparent outline-none resize-y rounded-lg px-2 py-1 -mx-2 border border-transparent leading-relaxed transition ${darkMode ? "hover:border-gray-700 focus:border-indigo-500" : "hover:border-gray-200 focus:border-gray-900"}`} />
                      <p className="text-xs text-gray-500">Click the subject or body to edit.</p>
                    </>
                  ) : (
                    <p className="text-gray-500 text-center py-12">Your generated email will appear here.</p>
                  )}
                </div>
              </div>

              <div className={`border-t px-8 py-5 flex justify-between ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white"}`}>
                <button onClick={handleSave} disabled={!dirty || !!busy}
                  className={`px-4 py-2 rounded-xl border flex items-center gap-2 transition ${
                    dirty
                      ? darkMode ? "border-indigo-500 text-white hover:bg-gray-800" : "border-gray-900 text-gray-900 hover:bg-gray-100"
                      : darkMode ? "border-gray-700 text-gray-400" : "text-gray-400 border-gray-200"
                  }`}>
                  <FiSave /> {busy === "saving" ? "Saving..." : dirty ? "Save changes" : generatedEmail ? "Saved" : "Auto-saved"}
                </button>
                <div className="flex gap-3">
                  <button onClick={() => { if (!generatedEmail) { setError("Generate an email first."); return; } setShowScheduleModal(true); }}
                    className={`px-4 py-2 rounded-xl border flex items-center gap-2 transition ${darkMode ? "border-gray-700 hover:bg-gray-800 text-white" : "border-gray-200 hover:bg-gray-100"}`}>
                    <FiCalendar /> Schedule
                  </button>
                  <button onClick={sendNow} disabled={!generatedEmail || sending}
                    className={`px-4 py-2 rounded-xl text-white flex gap-2 items-center disabled:opacity-50 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
                    <FiSend /> {sending ? "Sending..." : "Send Now"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>

      {showPlans && <UpgradeModal darkMode={darkMode} onClose={() => setShowPlans(false)} />}

      {showScheduleModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`w-[420px] rounded-3xl p-6 ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Schedule Email</h2>
              <button onClick={() => { setShowScheduleModal(false); setModalError(""); }}><FiX size={22} /></button>
            </div>
            <div className="mt-6 space-y-5">
              <div>
                <label className="text-sm text-gray-500">Select Date</label>
                <input type="date" value={scheduleData.date} onChange={(e) => setScheduleData({ ...scheduleData, date: e.target.value })}
                  className={`mt-2 w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-200"}`} />
              </div>
              <div>
                <label className="text-sm text-gray-500">Select Time</label>
                <input type="time" value={scheduleData.time} onChange={(e) => setScheduleData({ ...scheduleData, time: e.target.value })}
                  className={`mt-2 w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-200"}`} />
              </div>
            </div>
            {modalError && (
              <p className="mt-4 text-sm text-red-400 text-center">{modalError}</p>
            )}
            <button onClick={() => { if (!scheduleData.date || !scheduleData.time) { setModalError("Please select date and time."); return; } setModalError(""); scheduleEmail(); }}
              className={`mt-4 w-full py-3 rounded-xl text-white font-medium ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
              Schedule
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
