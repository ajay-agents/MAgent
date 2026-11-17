import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { FiSearch, FiEdit2, FiTrash2, FiFileText, FiCalendar, FiX, FiCheckCircle, FiSend, FiSave } from "react-icons/fi";

const fmt = (iso) => iso ? new Date(iso).toLocaleString() : "";
const purposeLabel = (s) => s?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "—";

export default function Drafts() {
  const { darkMode } = useTheme();

  const [drafts, setDrafts]           = useState([]);
  const [search, setSearch]           = useState("");
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [notification, setNotification]   = useState("");
  const [loading, setLoading]         = useState(true);
  const [sending, setSending]         = useState(null); // id of draft being sent
  const [edit, setEdit]               = useState({ subject: "", body: "" });
  const [saving, setSaving]           = useState(false);
  const [modalError, setModalError]   = useState("");

  const notify = (msg) => { setNotification(msg); setTimeout(() => setNotification(""), 3000); };

  useEffect(() => {
    api.get("/api/emails?status=draft&include_campaigns=false") // campaign emails are reviewed on their campaign
      .then(setDrafts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const deleteDraft = async (id) => {
    try {
      await api.delete(`/api/emails/${id}`);
      setDrafts((prev) => prev.filter((d) => d.id !== id));
      notify("Draft moved to trash");
    } catch (err) {
      notify(err.message);
    }
  };

  const sendDraft = async (draft) => {
    setSending(draft.id);
    try {
      await api.post(`/api/emails/${draft.id}/send`, {});
      setDrafts((prev) => prev.filter((d) => d.id !== draft.id));
      notify("Email sent successfully!");
    } catch (err) {
      notify(err.message || "Send failed. Check your Gmail credentials in Settings.");
    } finally {
      setSending(null);
    }
  };

  const openDraft = async (draft) => {
    setModalError("");
    try {
      const full = await api.get(`/api/emails/${draft.id}`);
      setSelectedDraft(full);
      setEdit({ subject: full.subject, body: full.body });
    } catch (err) {
      notify(err.message);
    }
  };

  const editDirty = !!selectedDraft && (edit.subject !== selectedDraft.subject || edit.body !== selectedDraft.body);

  const closeDraft = () => {
    if (editDirty && !window.confirm("Discard your unsaved changes?")) return;
    setSelectedDraft(null);
  };

  const saveDraft = async () => {
    if (!edit.subject.trim() || !edit.body.trim()) { setModalError("Subject and body can't be empty."); return; }
    setSaving(true);
    setModalError("");
    try {
      const saved = await api.patch(`/api/emails/${selectedDraft.id}`, { subject: edit.subject, body: edit.body });
      setDrafts((prev) => prev.map((d) => (d.id === saved.id ? { ...d, subject: saved.subject } : d)));
      setSelectedDraft(null);
      notify("Draft saved");
    } catch (err) {
      setModalError(err.message || "Saving failed.");
    } finally {
      setSaving(false);
    }
  };

  const filtered = drafts.filter((d) =>
    d.recipient_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.recipient_email?.toLowerCase().includes(search.toLowerCase()) ||
    d.purpose?.toLowerCase().includes(search.toLowerCase()) ||
    d.subject?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          {notification && (
            <div className={`mb-5 px-5 py-3 rounded-xl w-fit flex items-center gap-2 ${darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>
              <FiCheckCircle /> {notification}
            </div>
          )}

          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-extrabold flex items-center gap-3"><FiFileText /> Drafts</h1>
              <p className="mt-2 text-gray-500">Your saved AI email drafts</p>
            </div>
            <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${darkMode ? "bg-[#11141D] border-gray-700" : "bg-white border-gray-200"}`}>
              <FiSearch className="text-gray-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && setSearch("")}
                placeholder="Search drafts..."
                className={`bg-transparent outline-none w-56 ${darkMode ? "text-white placeholder:text-gray-500" : "text-gray-900"}`} />
            </div>
          </div>

          {loading && <p className="text-gray-500">Loading...</p>}

          {!loading && filtered.length === 0 && (
            <div className={`rounded-3xl p-12 text-center border shadow-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
              <FiFileText size={55} className="mx-auto mb-5 text-gray-400" />
              <h2 className="text-2xl font-bold">No Drafts Found</h2>
              <p className="mt-3 text-gray-500">Generate an email to create a draft.</p>
            </div>
          )}

          <div className="space-y-6">
            {filtered.map((draft) => (
              <div key={draft.id} className={`rounded-3xl p-6 shadow-xl border transition ${darkMode ? "bg-[#11141D] border-gray-800 hover:bg-[#151923]" : "bg-white border-gray-200 hover:bg-gray-50"}`}>
                <div className="flex justify-between">
                  <div>
                    <h2 className="text-xl font-bold">{draft.recipient_name || "No Recipient"}</h2>
                    <p className="text-gray-500">{draft.recipient_email}</p>
                  </div>
                  <div className="flex items-center gap-2 text-gray-500"><FiCalendar />{fmt(draft.created_at)}</div>
                </div>

                <div className="mt-4 grid md:grid-cols-3 gap-5">
                  <div><p className="text-sm text-gray-500">Purpose</p><p className="font-medium">{purposeLabel(draft.purpose)}</p></div>
                  <div><p className="text-sm text-gray-500">Tone</p><p className="font-medium capitalize">{draft.tone}</p></div>
                  <div><p className="text-sm text-gray-500">Length</p><p className="font-medium capitalize">{draft.length}</p></div>
                </div>

                <div className={`mt-4 p-4 rounded-2xl ${darkMode ? "bg-[#090B12]" : "bg-gray-100"}`}>
                  <p className="text-sm font-medium">Subject: {draft.subject}</p>
                </div>

                <div className="flex gap-3 mt-6">
                  <button onClick={() => openDraft(draft)}
                    className={`px-5 py-3 rounded-xl border flex items-center gap-2 ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                    <FiEdit2 /> View &amp; Edit
                  </button>
                  <button onClick={() => sendDraft(draft)} disabled={sending === draft.id}
                    className={`px-5 py-3 rounded-xl text-white flex items-center gap-2 disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
                    <FiSend /> {sending === draft.id ? "Sending..." : "Send Now"}
                  </button>
                  <button onClick={() => deleteDraft(draft.id)}
                    className="px-5 py-3 rounded-xl bg-red-500 hover:bg-red-600 text-white flex items-center gap-2">
                    <FiTrash2 /> Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </main>
      </div>

      {selectedDraft && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`w-[600px] max-h-[80vh] overflow-y-auto rounded-3xl p-6 shadow-2xl ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-2xl font-bold">Edit Draft</h2>
              <button onClick={closeDraft}><FiX size={25} /></button>
            </div>
            <p className="text-sm text-gray-500 mb-4">To {selectedDraft.recipient_name} &lt;{selectedDraft.recipient_email}&gt;</p>
            <label className="text-sm font-semibold text-gray-500 block mb-1">Subject</label>
            <input value={edit.subject} onChange={(e) => setEdit({ ...edit, subject: e.target.value })} maxLength={300}
              className={`w-full px-4 py-3 rounded-xl border outline-none font-medium mb-4 ${darkMode ? "bg-[#090B12] border-gray-700 text-white focus:border-indigo-500" : "bg-white border-gray-200 focus:border-gray-900"}`} />
            <label className="text-sm font-semibold text-gray-500 block mb-1">Body</label>
            <textarea value={edit.body} onChange={(e) => setEdit({ ...edit, body: e.target.value })} rows={12}
              className={`w-full px-4 py-3 rounded-xl border outline-none resize-y leading-relaxed ${darkMode ? "bg-[#090B12] border-gray-700 text-white focus:border-indigo-500" : "bg-white border-gray-200 focus:border-gray-900"}`} />
            {modalError && <p className="mt-3 text-sm text-red-400">{modalError}</p>}
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={closeDraft}
                className={`px-5 py-3 rounded-xl border ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                Cancel
              </button>
              <button onClick={saveDraft} disabled={!editDirty || saving}
                className={`px-5 py-3 rounded-xl text-white flex items-center gap-2 disabled:opacity-50 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
                <FiSave /> {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
