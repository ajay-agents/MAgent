import React, { useState, useEffect, useRef, useCallback } from "react";
import { FiSearch, FiBell, FiMoon, FiSun, FiSend, FiClock, FiFileText, FiAlertCircle } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const STATUS_ICON = {
  sent:    <FiSend    className="text-green-400"  size={13} />,
  pending: <FiClock   className="text-blue-400"   size={13} />,
  draft:   <FiFileText className="text-gray-400"  size={13} />,
  failed:  <FiAlertCircle className="text-red-400" size={13} />,
};

const fmt = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

const Navbar = () => {
  const { darkMode, toggleTheme } = useTheme();
  const { user } = useAuth();

  const displayName = user?.email
    ? user.email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "User";
  const initial = displayName.charAt(0).toUpperCase();

  const [showNotif, setShowNotif]   = useState(false);
  const [notifs, setNotifs]         = useState([]);
  const [unread, setUnread]         = useState(0);
  const bellRef                     = useRef(null);

  const fetchNotifs = useCallback(async () => {
    try {
      const emails = await api.get("/api/emails");
      const recent = emails.slice(0, 8);
      setNotifs(recent);
      setUnread(emails.filter((e) => e.status === "pending").length);
    } catch (_) {}
  }, []);

  useEffect(() => {
    fetchNotifs();
  }, [fetchNotifs]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => { if (bellRef.current && !bellRef.current.contains(e.target)) setShowNotif(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggleNotif = () => {
    if (!showNotif) fetchNotifs();
    setShowNotif((v) => !v);
  };

  return (
    <div
      className={`h-18 px-8 flex items-center justify-between border-b backdrop-blur transition-all duration-500 ${
        darkMode ? "bg-[#090B12]/90 border-gray-800" : "bg-white/70 border-gray-200"
      }`}
    >
      {/* SEARCH */}
      <div className="relative w-[520px]">
        <FiSearch className={`absolute left-4 top-1/2 -translate-y-1/2 ${darkMode ? "text-gray-500" : "text-gray-400"}`} />
        <input
          type="text"
          placeholder="Search emails, templates, campaigns..."
          className={`w-full h-12 pl-11 pr-4 rounded-xl border outline-none transition ${
            darkMode
              ? "bg-[#11141D] border-gray-800 text-white placeholder:text-gray-500 focus:ring-2 focus:ring-purple-500"
              : "bg-white border-gray-200 text-gray-900 focus:ring-2 focus:ring-gray-300"
          }`}
        />
      </div>

      {/* RIGHT SIDE */}
      <div className="flex items-center gap-5">

        {/* NOTIFICATION BELL */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={toggleNotif}
            className={`relative p-3 rounded-xl transition shadow-sm ${
              darkMode ? "bg-[#11141D] text-white hover:bg-[#181c27]" : "bg-white text-gray-700 hover:shadow-md"
            }`}
          >
            <FiBell className="text-lg" />
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unread}
              </span>
            )}
          </button>

          {showNotif && (
            <div className={`absolute right-0 top-14 w-80 rounded-2xl shadow-2xl border z-50 overflow-hidden ${
              darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"
            }`}>
              <div className={`px-4 py-3 border-b font-semibold text-sm flex justify-between items-center ${
                darkMode ? "border-gray-800 text-white" : "border-gray-100 text-gray-800"
              }`}>
                <span>Recent Activity</span>
                {unread > 0 && <span className="text-xs text-blue-400">{unread} scheduled</span>}
              </div>

              {notifs.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-400 text-sm">No emails yet</div>
              ) : (
                <div className="max-h-72 overflow-y-auto divide-y divide-gray-800/30">
                  {notifs.map((e) => (
                    <div key={e.id} className={`px-4 py-3 flex items-start gap-3 hover:bg-gray-500/10 transition`}>
                      <div className="mt-0.5">{STATUS_ICON[e.status] || STATUS_ICON.draft}</div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${darkMode ? "text-white" : "text-gray-800"}`}>
                          {e.subject}
                        </p>
                        <p className="text-xs text-gray-500 truncate">To: {e.recipient_name} · {e.status}</p>
                        <p className="text-xs text-gray-500">{fmt(e.created_at)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* DARK MODE TOGGLE */}
        <button
          onClick={toggleTheme}
          className={`p-3 rounded-xl transition shadow-sm ${
            darkMode ? "bg-[#11141D] text-yellow-300 hover:bg-[#181c27]" : "bg-white text-gray-700 hover:shadow-md"
          }`}
        >
          {darkMode ? <FiSun /> : <FiMoon />}
        </button>

        {/* PROFILE */}
        <div className={`flex items-center gap-3 pl-3 pr-4 py-2 rounded-xl transition cursor-pointer ${
          darkMode ? "bg-[#11141D] hover:bg-[#181c27]" : "bg-white shadow-sm hover:shadow-md"
        }`}>
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
            darkMode ? "bg-gradient-to-br from-indigo-500 to-purple-600" : "bg-gradient-to-br from-gray-900 to-gray-600"
          }`}>
            {initial}
          </div>
          <div className="text-sm leading-tight">
            <p className={`font-semibold ${darkMode ? "text-white" : "text-gray-800"}`}>{displayName}</p>
            <p className="text-gray-400 text-xs">Pro User</p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Navbar;
