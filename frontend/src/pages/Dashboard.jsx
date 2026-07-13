import { useEffect, useState, useCallback } from "react";
import { FiPlus, FiSend, FiClock } from "react-icons/fi";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

export default function Dashboard() {
  const { darkMode } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState({ generated: 0, sent: 0, scheduled: 0, failed: 0 });

  const fetchStats = useCallback(async () => {
    try {
      const all = await api.get("/api/emails");
      setStats({
        generated: all.length,
        sent:      all.filter((e) => e.status === "sent").length,
        scheduled: all.filter((e) => e.status === "pending").length,
        failed:    all.filter((e) => e.status === "failed").length,
      });
    } catch (_) {}
  }, []);

  useEffect(() => {
    fetchStats();
    window.addEventListener("focus", fetchStats);
    return () => window.removeEventListener("focus", fetchStats);
  }, [fetchStats]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";

  return (
    <div className={`flex min-h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="mb-10">
            <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>{greeting} 👋</p>
            <h1 className="text-4xl font-bold mt-2">Welcome Back{user?.email ? `, ${user.email.split("@")[0]}` : ""}</h1>
            <p className={`mt-3 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Create and manage your AI emails in one place.</p>
            <button onClick={() => navigate("/create-email")}
              className={`mt-8 flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all duration-300 hover:scale-[1.03] shadow-lg ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-500 to-blue-500 text-white shadow-purple-500/30" : "bg-gradient-to-r from-gray-900 to-black text-white hover:shadow-xl"}`}>
              <FiPlus className="text-lg" /> Create Email
            </button>
          </div>

          <h2 className="text-xl font-semibold mb-5">Quick Actions</h2>
          <div className="grid gap-6 md:grid-cols-3">
            <Card title="Create Email"  desc="Generate a new AI email instantly."   icon={<FiPlus className="text-xl" />}  path="/create-email" />
            <Card title="Scheduled"     desc="View all scheduled emails."            icon={<FiClock className="text-xl" />} path="/scheduled-emails" />
            <Card title="Sent Emails"   desc="See emails that have been sent."       icon={<FiSend className="text-xl" />}  path="/sent-emails" />
          </div>

          <h2 className="text-xl font-semibold mt-12 mb-5">Overview</h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Emails Generated" value={stats.generated} />
            <StatCard title="Emails Sent"      value={stats.sent} />
            <StatCard title="Scheduled"        value={stats.scheduled} />
            <StatCard title="Failed"           value={stats.failed} />
          </div>
        </main>
      </div>
    </div>
  );
}

function Card({ title, desc, icon, path }) {
  const { darkMode } = useTheme();
  const navigate = useNavigate();
  return (
    <div onClick={() => navigate(path)}
      className={`rounded-2xl border p-6 transition-all duration-300 group cursor-pointer hover:-translate-y-2 ${darkMode ? "bg-[#11141D] border-gray-800 hover:border-purple-500/60 hover:shadow-xl hover:shadow-purple-500/10" : "bg-white border-gray-200 hover:border-blue-300 hover:shadow-xl"}`}>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110 ${darkMode ? "bg-gradient-to-br from-indigo-500/20 via-purple-500/20 to-blue-500/20 text-blue-400 shadow-lg shadow-purple-500/20" : "bg-gradient-to-br from-blue-100 to-indigo-100 text-blue-600"}`}>{icon}</div>
      <h3 className="mt-5 text-lg font-semibold">{title}</h3>
      <p className={`mt-2 text-sm leading-6 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>{desc}</p>
    </div>
  );
}

function StatCard({ title, value }) {
  const { darkMode } = useTheme();
  return (
    <div className={`rounded-2xl border p-6 transition-all duration-300 hover:-translate-y-1 ${darkMode ? "bg-[#11141D] border-gray-800 hover:border-purple-500/50 hover:shadow-lg hover:shadow-purple-500/10" : "bg-white border-gray-200 hover:border-blue-300 hover:shadow-lg"}`}>
      <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>{title}</p>
      <h2 className="mt-3 text-4xl font-bold">{value}</h2>
    </div>
  );
}
