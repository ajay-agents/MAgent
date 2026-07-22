import { useState, useEffect, useCallback } from "react";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { FiRefreshCw, FiMail, FiCheckCircle, FiXCircle, FiSearch } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";

const fmtTime = (iso) => iso ? new Date(iso).toLocaleString() : "—";

export default function SentEmails() {
  const { darkMode } = useTheme();
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]       = useState("All");
  const [search, setSearch] = useState("");

  const fetchEmails = useCallback(async () => {
    setLoading(true);
    try {
      const [sent, failed] = await Promise.all([
        api.get("/api/emails?status=sent"),
        api.get("/api/emails?status=failed"),
      ]);
      setEmails([...sent, ...failed].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
    } catch (_) {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchEmails(); }, [fetchEmails]);

  const byTab     = tab === "All" ? emails : emails.filter((e) => e.status === tab.toLowerCase());
  const displayed = search.trim()
    ? byTab.filter((e) =>
        e.recipient_email?.toLowerCase().includes(search.toLowerCase()) ||
        e.recipient_name?.toLowerCase().includes(search.toLowerCase()) ||
        e.subject?.toLowerCase().includes(search.toLowerCase())
      )
    : byTab;
  const sentCount   = emails.filter((e) => e.status === "sent").length;
  const failedCount = emails.filter((e) => e.status === "failed").length;

  const getStatusStyle = (status) =>
    status === "sent"
      ? darkMode ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" : "bg-emerald-50 text-emerald-700 border-emerald-200"
      : darkMode ? "bg-red-500/20 text-red-300 border-red-500/30" : "bg-red-50 text-red-600 border-red-200";

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-start mb-8">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl ${darkMode ? "bg-blue-500/20 text-blue-300" : "bg-blue-100 text-blue-600"}`}><FiMail size={24} /></div>
                <div>
                  <h1 className="text-3xl font-bold">Sent Emails</h1>
                  <p className="text-gray-500 text-sm mt-1">Track delivered emails and monitor failed attempts.</p>
                </div>
              </div>
              <button onClick={fetchEmails}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl border transition ${darkMode ? "bg-[#11141D] border-gray-700 text-gray-300 hover:bg-gray-800" : "bg-white border-gray-200 text-gray-700 hover:bg-gray-100"}`}>
                <FiRefreshCw size={16} /> Refresh
              </button>
            </div>

            <div className="grid grid-cols-3 gap-5 mb-8">
              <StatBox label="Total Emails" value={emails.length} darkMode={darkMode} />
              <StatBox label="Successfully Sent" value={sentCount} color="text-emerald-500" icon={<FiCheckCircle size={28} className="text-emerald-500" />} darkMode={darkMode} />
              <StatBox label="Failed" value={failedCount} color="text-red-500" icon={<FiXCircle size={28} className="text-red-500" />} darkMode={darkMode} />
            </div>

            <div className="flex items-center justify-between mb-5">
              <div className="flex gap-2">
              {["All", "Sent", "Failed"].map((item) => (
                <button key={item} onClick={() => setTab(item)}
                  className={`px-5 py-2 rounded-xl text-sm font-medium transition ${tab === item ? darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white" : "bg-gray-900 text-white" : darkMode ? "text-gray-400 hover:text-white" : "text-gray-500 hover:text-gray-900"}`}>
                  {item}
                </button>
              ))}
              </div>
              <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border ${darkMode ? "bg-[#11141D] border-gray-700" : "bg-white border-gray-200"}`}>
                <FiSearch className="text-gray-400" size={15} />
                <input value={search} onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && setSearch("")}
                  placeholder="Search by recipient or subject..."
                  className={`bg-transparent outline-none w-64 text-sm ${darkMode ? "text-white placeholder:text-gray-500" : "text-gray-900"}`} />
              </div>
            </div>

            <div className={`rounded-2xl border overflow-hidden shadow-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
              <div className={`grid grid-cols-4 px-6 py-4 border-b text-xs font-semibold uppercase text-gray-500 ${darkMode ? "bg-[#151923] border-gray-800" : "bg-gray-50"}`}>
                <div>Recipient</div><div>Subject</div><div>Status</div><div>Time</div>
              </div>
              {loading ? (
                <div className="p-10 text-center text-gray-500">Loading...</div>
              ) : displayed.length === 0 ? (
                <div className="p-10 text-center text-gray-500">No emails found</div>
              ) : displayed.map((email) => (
                <div key={email.id} className={`grid grid-cols-4 px-6 py-5 items-center border-b transition ${darkMode ? "border-gray-800 hover:bg-[#151923]" : "hover:bg-gray-50"}`}>
                  <div className="font-medium">{email.recipient_email}</div>
                  <div className="text-gray-500">{email.subject}</div>
                  <div>
                    <span className={`px-3 py-1 rounded-full border text-xs font-medium capitalize ${getStatusStyle(email.status)}`}>{email.status}</span>
                  </div>
                  <div className="text-gray-500 text-sm">{fmtTime(email.sent_at || email.created_at)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value, color, icon, darkMode }) {
  return (
    <div className={`border rounded-2xl p-5 shadow-sm ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white"}`}>
      {icon ? (
        <div className="flex justify-between">
          <div><p className="text-sm text-gray-500">{label}</p><h2 className={`text-3xl font-bold mt-2 ${color}`}>{value}</h2></div>
          {icon}
        </div>
      ) : (
        <><p className="text-sm text-gray-500">{label}</p><h2 className="text-3xl font-bold mt-2">{value}</h2></>
      )}
    </div>
  );
}
