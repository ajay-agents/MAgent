import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { FiTrash2, FiRotateCcw, FiSearch, FiCheck } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";

const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

const DeletedEmails = () => {
  const { darkMode } = useTheme();

  const [emailList, setEmailList] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState("");
  const [message, setMessage]     = useState("");

  const notify = (msg) => { setMessage(msg); setTimeout(() => setMessage(""), 2500); };

  const fetchDeleted = () => {
    setLoading(true);
    api.get("/api/emails?status=deleted")
      .then(setEmailList)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDeleted(); }, []);

  const handleRestore = async (email) => {
    try {
      await api.post(`/api/emails/${email.id}/restore`, {});
      setEmailList((prev) => prev.filter((e) => e.id !== email.id));
      notify(`"${email.subject}" restored to drafts`);
    } catch (err) {
      notify(err.message);
    }
  };

  const handlePermanentDelete = async (email) => {
    if (!window.confirm(`Permanently delete "${email.subject}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/api/emails/${email.id}/permanent`);
      setEmailList((prev) => prev.filter((e) => e.id !== email.id));
      notify(`"${email.subject}" permanently deleted`);
    } catch (err) {
      notify(err.message);
    }
  };

  const filtered = emailList.filter(
    (e) =>
      e.recipient_name?.toLowerCase().includes(search.toLowerCase()) ||
      e.recipient_email?.toLowerCase().includes(search.toLowerCase()) ||
      e.subject?.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">

            {message && (
              <div className={`mb-5 flex items-center gap-2 px-5 py-3 rounded-xl w-fit ${darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>
                <FiCheck /> {message}
              </div>
            )}

            <div className="flex justify-between items-start mb-8">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl ${darkMode ? "bg-red-500/20 text-red-300" : "bg-red-100 text-red-600"}`}>
                  <FiTrash2 size={24} />
                </div>
                <div>
                  <h1 className="text-3xl font-bold">Deleted Emails</h1>
                  <p className="text-sm text-gray-500 mt-1">Manage emails moved to trash.</p>
                </div>
              </div>
              <div className={`px-5 py-3 rounded-xl border ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
                <p className="text-sm text-gray-500">Trash Items</p>
                <h2 className="text-2xl font-bold">{emailList.length}</h2>
              </div>
            </div>

            <div className="mb-6">
              <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border max-w-md ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
                <FiSearch className="text-gray-400" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search deleted emails..."
                  className={`bg-transparent outline-none w-full text-sm ${darkMode ? "text-white placeholder-gray-500" : "text-gray-800"}`}
                />
              </div>
            </div>

            <div className={`rounded-2xl border overflow-hidden shadow-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
              <div className={`grid grid-cols-5 px-6 py-4 border-b text-xs font-semibold uppercase text-gray-500 ${darkMode ? "bg-[#151923] border-gray-800" : "bg-gray-50"}`}>
                <div>Recipient</div>
                <div>Subject</div>
                <div>Purpose</div>
                <div>Deleted At</div>
                <div>Actions</div>
              </div>

              {loading ? (
                <div className="p-10 text-center text-gray-500">Loading...</div>
              ) : filtered.length === 0 ? (
                <div className="p-10 text-center text-gray-500">No deleted emails</div>
              ) : filtered.map((email) => (
                <div
                  key={email.id}
                  className={`grid grid-cols-5 px-6 py-5 items-center border-b transition ${darkMode ? "border-gray-800 hover:bg-[#151923]" : "border-gray-100 hover:bg-gray-50"}`}
                >
                  <div>
                    <p className="font-medium">{email.recipient_name}</p>
                    <p className="text-sm text-gray-500">{email.recipient_email}</p>
                  </div>
                  <div className="text-gray-500 truncate pr-4">{email.subject}</div>
                  <div className="text-gray-500 capitalize">{email.purpose?.replace("_", " ")}</div>
                  <div className="text-gray-500 text-sm">{fmtDate(email.deleted_at)}</div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleRestore(email)}
                      className={`p-2 rounded-lg ${darkMode ? "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30" : "bg-blue-50 text-blue-600 hover:bg-blue-100"}`}
                      title="Restore to drafts"
                    >
                      <FiRotateCcw size={17} />
                    </button>
                    <button
                      onClick={() => handlePermanentDelete(email)}
                      className={`p-2 rounded-lg ${darkMode ? "bg-red-500/20 text-red-300 hover:bg-red-500/30" : "bg-red-50 text-red-600 hover:bg-red-100"}`}
                      title="Delete permanently"
                    >
                      <FiTrash2 size={17} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default DeletedEmails;
