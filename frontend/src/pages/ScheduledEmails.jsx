import { useState, useEffect } from "react";
import { FiSearch, FiEye, FiCalendar, FiTrash2, FiX } from "react-icons/fi";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";

const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—";
const fmtTime = (iso) => iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
const initials = (name) => name?.split(" ").map((w) => w[0]).join("").toUpperCase() || "?";

export default function ScheduledEmails() {
  const { darkMode } = useTheme();

  const [emailList, setEmailList]       = useState([]);
  const [loading, setLoading]           = useState(true);
  const [search, setSearch]             = useState("");
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [showModal, setShowModal]       = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [scheduleData, setScheduleData] = useState({ date: "", time: "" });
  const [notification, setNotification] = useState("");

  const notify = (msg) => { setNotification(msg); setTimeout(() => setNotification(""), 3000); };

  const fetchEmails = () => {
    setLoading(true);
    api.get("/api/emails?status=pending")
      .then(setEmailList)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchEmails(); }, []);

  const handleCancel = async (id) => {
    try {
      await api.delete(`/api/emails/${id}/schedule`);
      setEmailList((prev) => prev.filter((m) => m.id !== id));
      notify("Schedule cancelled — moved back to drafts");
    } catch (err) {
      notify(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/emails/${id}`);
      setEmailList((prev) => prev.filter((m) => m.id !== id));
      notify("Email moved to trash");
    } catch (err) {
      notify(err.message);
    }
  };

  const handleReschedule = async () => {
    if (!selectedEmail || !scheduleData.date || !scheduleData.time) return;
    const scheduledAt = new Date(`${scheduleData.date}T${scheduleData.time}:00`).toISOString();
    try {
      // cancel then reschedule
      await api.delete(`/api/emails/${selectedEmail.id}/schedule`);
      await api.post(`/api/emails/${selectedEmail.id}/schedule`, { scheduled_at: scheduledAt });
      notify("Email rescheduled");
      setShowSchedule(false);
      fetchEmails();
    } catch (err) {
      notify(err.message);
    }
  };

  const filtered = emailList.filter((m) =>
    m.recipient_name?.toLowerCase().includes(search.toLowerCase()) ||
    m.recipient_email?.toLowerCase().includes(search.toLowerCase()) ||
    m.subject?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          {notification && (
            <div className={`mb-5 px-5 py-3 rounded-xl w-fit ${darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>{notification}</div>
          )}

          <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-start">
              <div>
                <h1 className={`text-4xl font-bold ${darkMode ? "text-white" : "text-gray-900"}`}>Scheduled Emails</h1>
                <p className={`mt-2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Emails queued to be sent later.</p>
              </div>
              <p className="text-gray-400 mt-3">{filtered.length} email{filtered.length !== 1 ? "s" : ""}</p>
            </div>

            <div className="flex justify-end mt-8">
              <div className="relative">
                <FiSearch className="absolute left-4 top-4 text-gray-400" />
                <input value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by name, email or subject..."
                  className={`w-96 pl-11 pr-5 py-3 rounded-2xl border outline-none ${darkMode ? "bg-[#11141D] border-gray-700 text-white placeholder:text-gray-500" : "bg-white border-gray-200"}`} />
              </div>
            </div>

            <div className={`mt-8 rounded-3xl border shadow-xl overflow-hidden ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
              <table className="w-full">
                <thead className={`border-b ${darkMode ? "bg-[#151923] border-gray-800" : "bg-gray-50"}`}>
                  <tr>
                    {["RECIPIENT","SUBJECT","SCHEDULED","STATUS","ACTIONS"].map((h) => (
                      <th key={h} className="text-left text-xs tracking-wider text-gray-500 px-6 py-5">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={5} className="text-center py-10 text-gray-500">Loading...</td></tr>
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={5} className="text-center py-10 text-gray-500">No scheduled emails</td></tr>
                  ) : filtered.map((mail) => (
                    <tr key={mail.id} className={`border-b transition ${darkMode ? "border-gray-800 hover:bg-[#151923]" : "hover:bg-gray-50"}`}>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center font-semibold ${darkMode ? "bg-cyan-500/20 text-cyan-300" : "bg-cyan-100 text-cyan-700"}`}>
                            {initials(mail.recipient_name)}
                          </div>
                          <div>
                            <h3 className="font-semibold">{mail.recipient_name}</h3>
                            <p className="text-sm text-gray-500">{mail.recipient_email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <h3 className="font-medium">{mail.subject}</h3>
                      </td>
                      <td className="px-6 py-5">
                        <h3 className="font-medium">{fmtDate(mail.scheduled_at)}</h3>
                        <p className="text-sm text-gray-500">{fmtTime(mail.scheduled_at)}</p>
                      </td>
                      <td className="px-6 py-5">
                        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${darkMode ? "bg-orange-500/20 text-orange-300" : "bg-orange-100 text-orange-600"}`}>
                          <span className="w-2 h-2 rounded-full bg-current" /> Pending
                        </span>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex justify-end gap-4">
                          <button onClick={() => { setSelectedEmail(mail); setShowModal(true); }}
                            className={`w-9 h-9 rounded-lg border flex items-center justify-center ${darkMode ? "border-gray-700 hover:bg-gray-800" : "hover:bg-gray-100"}`}>
                            <FiEye />
                          </button>
                          <button onClick={() => { setSelectedEmail(mail); setScheduleData({ date: "", time: "" }); setShowSchedule(true); }}
                            className={`w-9 h-9 rounded-lg border flex items-center justify-center ${darkMode ? "border-gray-700 hover:bg-gray-800" : "hover:bg-gray-100"}`}>
                            <FiCalendar />
                          </button>
                          <button onClick={() => handleDelete(mail.id)}
                            className={`w-9 h-9 rounded-lg border text-red-500 flex items-center justify-center ${darkMode ? "border-gray-700 hover:bg-red-500/10" : "hover:bg-red-50"}`}>
                            <FiTrash2 />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>

      {showModal && selectedEmail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`w-[450px] rounded-3xl p-6 ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Email Preview</h2>
              <button onClick={() => setShowModal(false)}><FiX size={22} /></button>
            </div>
            <div className="mt-6 space-y-4">
              <div><p className="text-sm text-gray-500">Recipient</p><p className="font-medium">{selectedEmail.recipient_name}</p></div>
              <div><p className="text-sm text-gray-500">Email</p><p className="font-medium">{selectedEmail.recipient_email}</p></div>
              <div><p className="text-sm text-gray-500">Subject</p><p className="font-medium">{selectedEmail.subject}</p></div>
              <div><p className="text-sm text-gray-500">Scheduled</p><p className="font-medium">{fmtDate(selectedEmail.scheduled_at)} at {fmtTime(selectedEmail.scheduled_at)}</p></div>
            </div>
            <button onClick={() => setShowModal(false)}
              className={`mt-6 w-full py-3 rounded-xl text-white font-medium ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>Close</button>
          </div>
        </div>
      )}

      {showSchedule && selectedEmail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`w-[420px] rounded-3xl p-6 ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Reschedule Email</h2>
              <button onClick={() => setShowSchedule(false)}><FiX size={22} /></button>
            </div>
            <div className="mt-6 space-y-5">
              <div>
                <label className="text-sm text-gray-500">Select Date</label>
                <input type="date" value={scheduleData.date} onChange={(e) => setScheduleData({ ...scheduleData, date: e.target.value })}
                  className={`mt-2 w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700" : "bg-white border-gray-200"}`} />
              </div>
              <div>
                <label className="text-sm text-gray-500">Select Time</label>
                <input type="time" value={scheduleData.time} onChange={(e) => setScheduleData({ ...scheduleData, time: e.target.value })}
                  className={`mt-2 w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700" : "bg-white border-gray-200"}`} />
              </div>
            </div>
            <button onClick={handleReschedule}
              className={`mt-6 w-full py-3 rounded-xl text-white font-medium ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>Schedule</button>
          </div>
        </div>
      )}
    </div>
  );
}
