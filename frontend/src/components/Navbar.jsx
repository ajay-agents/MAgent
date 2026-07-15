import React from "react";
import { FiSearch, FiBell, FiMoon, FiSun } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { darkMode, toggleTheme } = useTheme();
  const { user } = useAuth();

  // Derive display name from email: "ajay.rajput@gmail.com" → "Ajay Rajput"
  const displayName = user?.email
    ? user.email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "User";
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div
      className={`h-18 px-8 flex items-center justify-between border-b backdrop-blur transition-all duration-500 ${
        darkMode
          ? "bg-[#090B12]/90 border-gray-800"
          : "bg-white/70 border-gray-200"
      }`}
    >
      {/* SEARCH */}

      <div className="relative w-[520px]">
        <FiSearch
          className={`absolute left-4 top-1/2 -translate-y-1/2 ${
            darkMode ? "text-gray-500" : "text-gray-400"
          }`}
        />

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
        {/* NOTIFICATION */}

        <button
          className={`relative p-3 rounded-xl transition shadow-sm ${
            darkMode
              ? "bg-[#11141D] text-white hover:bg-[#181c27]"
              : "bg-white text-gray-700 hover:shadow-md"
          }`}
        >
          <FiBell className="text-lg" />

          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
        </button>

        {/* DARK MODE TOGGLE */}

        <button
          onClick={toggleTheme}
          className={`p-3 rounded-xl transition shadow-sm ${
            darkMode
              ? "bg-[#11141D] text-yellow-300 hover:bg-[#181c27]"
              : "bg-white text-gray-700 hover:shadow-md"
          }`}
        >
          {darkMode ? <FiSun /> : <FiMoon />}
        </button>

        {/* PROFILE */}

        <div
          className={`flex items-center gap-3 pl-3 pr-4 py-2 rounded-xl transition cursor-pointer ${
            darkMode
              ? "bg-[#11141D] hover:bg-[#181c27]"
              : "bg-white shadow-sm hover:shadow-md"
          }`}
        >
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
              darkMode
                ? "bg-gradient-to-br from-indigo-500 to-purple-600"
                : "bg-gradient-to-br from-gray-900 to-gray-600"
            }`}
          >
            {initial}
          </div>

          <div className="text-sm leading-tight">
            <p
              className={`font-semibold ${
                darkMode ? "text-white" : "text-gray-800"
              }`}
            >
              {displayName}
            </p>

            <p className="text-gray-400 text-xs">{user?.email || ""}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Navbar;
