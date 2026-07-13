import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";
import { FiCalendar, FiSend, FiMessageSquare, FiCopy, FiCheckCircle, FiX } from "react-icons/fi";
import { HiSparkles } from "react-icons/hi2";

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
  const [generatedEmail, setGeneratedEmail] = useState(null); // { id, subject, body }
  const [notification, setNotification]     = useState("");
  const [scheduleData, setScheduleData]     = useState({ date: "", time: "" });
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [error, setError]                   = useState("");
  const [modalError, setModalError]         = useState("");

  const notify = (msg) => { setNotification(msg); setTimeout(() => setNotification(""), 3000); };

  const handleChange = (name, value) => setFormData((prev) => ({ ...prev, [name]: value }));

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
      setGeneratedEmail(result); // { id, subject, body, ai_model, ... }
      notify("Email generated and saved as draft");
    } catch (err) {
      setError(err.message || "Generation failed. Check your API key.");
    } finally {
      setLoading(false);
    }
  };

  const copyEmail = () => {
    if (!generatedEmail) return;
    navigator.clipboard.writeText(`Subject: ${generatedEmail.subject}\n\n${generatedEmail.body}`);
    notify("Email copied to clipboard");
  };

  const scheduleEmail = async () => {
    if (!generatedEmail) return;
    const scheduledAt = new Date(`${scheduleData.date}T${scheduleData.time}:00`).toISOString();
    try {
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
            <div className="mb-3 px-5 py-3 rounded-xl w-fit flex items-center gap-2 bg-red-500/10 text-red-400 border border-red-400/30">
              {error}
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
                <button onClick={handleGenerate} disabled={loading}
                  className={`px-4 py-2 rounded-xl border ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                  Regenerate
                </button>
              </div>

              <div className="flex-1 p-8 overflow-y-auto">
                <div className={`rounded-2xl shadow-lg p-6 space-y-5 border ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
                  {generatedEmail ? (
                    <>
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Subject</p>
                          <p className="font-semibold">{generatedEmail.subject}</p>
                        </div>
                        <button onClick={copyEmail} className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                          <FiCopy /> Copy
                        </button>
                      </div>
                      <hr className={darkMode ? "border-gray-800" : "border-gray-200"} />
                      <p className="whitespace-pre-line">{generatedEmail.body}</p>
                    </>
                  ) : (
                    <p className="text-gray-500 text-center py-12">Your generated email will appear here.</p>
                  )}
                </div>
              </div>

              <div className={`border-t px-8 py-5 flex justify-between ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white"}`}>
                <button className={`px-4 py-2 rounded-xl border flex items-center gap-2 ${darkMode ? "border-gray-700 text-gray-400" : "text-gray-400 border-gray-200"}`} disabled>
                  <FiMessageSquare /> Auto-saved
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
