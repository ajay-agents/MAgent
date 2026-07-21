import React from "react";
import { NavLink } from "react-router-dom";

import {
  FiGrid,
  FiMail,
  FiClock,
  FiSend,
  FiSettings,
  FiLogOut,
  FiTrash2,
  FiFileText,
} from "react-icons/fi";

import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

const Sidebar = () => {
  const { darkMode } = useTheme();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const hasDraft = localStorage.getItem("hasDraft") === "true";

  return (
    <div
      className={`w-72 h-screen flex flex-col border-r transition-all duration-500 ${
        darkMode
          ? "bg-[#090B12] border-gray-800 text-white"
          : "bg-white border-gray-200 text-gray-900"
      }`}
    >
      {/* BRAND */}

      <div
        className={`px-8 py-7 border-b ${
          darkMode ? "border-gray-800" : "border-gray-200"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              darkMode
                ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30"
                : "bg-gray-900 text-white"
            }`}
          >
            <FiMail size={18} />
          </div>

          <div>
            <h2 className="text-xl font-bold">MailFlow AI</h2>

            <p
              className={`text-xs ${
                darkMode ? "text-gray-400" : "text-gray-500"
              }`}
            >
              AI Outreach
            </p>
          </div>
        </div>
      </div>

      {/* MENU */}

      <div className="flex-1 px-5 py-6 space-y-2">
        <SideItem to="/dashboard" icon={<FiGrid />} label="Dashboard" />

        <SideItem to="/create-email" icon={<FiMail />} label="Create Email" />

        <SideItem
          to="/drafts"
          icon={<FiFileText />}
          label="Drafts"
          highlight={hasDraft}
        />

        <SideItem to="/scheduled-emails" icon={<FiClock />} label="Scheduled" />

        <SideItem to="/sent-emails" icon={<FiSend />} label="Sent Emails" />

        <SideItem
          to="/deleted-emails"
          icon={<FiTrash2 />}
          label="Deleted Emails"
        />

        <SideItem to="/settings" icon={<FiSettings />} label="Settings" />
      </div>

      {/* LOGOUT */}

      <div
        className={`p-5 border-t ${
          darkMode ? "border-gray-800" : "border-gray-200"
        }`}
      >
        <button
          onClick={handleLogout}
          className={`w-full flex items-center gap-3 justify-center py-3 rounded-xl transition font-medium ${
            darkMode
              ? "bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 text-white shadow-lg shadow-purple-500/20 hover:scale-105"
              : "bg-gray-900 hover:bg-black text-white"
          }`}
        >
          <FiLogOut />
          Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;

/* SIDE ITEM */

function SideItem({ to, icon, label, highlight }) {
  const { darkMode } = useTheme();

  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-5 py-3 rounded-xl transition-all duration-300 text-sm font-medium

        ${
          isActive
            ? darkMode
              ? "bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-blue-500/20 text-indigo-300 border border-purple-500/30 shadow-lg shadow-purple-500/10"
              : "bg-gray-900 text-white"
            : highlight
              ? darkMode
                ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                : "bg-gray-100 text-gray-900"
              : darkMode
                ? "text-gray-400 hover:bg-[#11141D] hover:text-white"
                : "text-gray-600 hover:bg-gray-100"
        }

        `
      }
    >
      <span
        className={`
          text-lg
          ${highlight ? "text-purple-500" : darkMode ? "text-indigo-300" : ""}
        `}
      >
        {icon}
      </span>

      {label}
    </NavLink>
  );
}
