import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { FiBell, FiMoon, FiShield, FiLogOut, FiMail, FiCheckCircle } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

export default function Settings() {
  const { darkMode, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [mailbox, setMailbox]         = useState(null);
  const [gmailForm, setGmailForm]     = useState({ gmail_address: "", app_password: "" });
  const [notification, setNotification] = useState("");
  const [gmailLoading, setGmailLoading] = useState(false);

  const notify = (msg) => { setNotification(msg); setTimeout(() => setNotification(""), 4000); };

  useEffect(() => {
    api.get("/api/mailbox").then(setMailbox).catch(() => {});
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const saveMailbox = async (e) => {
    e.preventDefault();
    setGmailLoading(true);
    try {
      const result = await api.post("/api/mailbox", {
        gmail_address: gmailForm.gmail_address,
        app_password:  gmailForm.app_password.replace(/\s/g, ""),
      });
      setMailbox(result);
      setGmailForm({ gmail_address: "", app_password: "" });
      notify("Gmail credentials saved successfully");
    } catch (err) {
      notify(err.message || "Failed to save credentials");
    } finally {
      setGmailLoading(false);
    }
  };

  const removeMailbox = async () => {
    try {
      await api.delete("/api/mailbox");
      setMailbox(null);
      notify("Gmail credentials removed");
    } catch (err) {
      notify(err.message);
    }
  };

  const email = user?.email || "—";
  const displayName = email.split("@")[0];
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-5xl mx-auto">
            {notification && (
              <div className={`mb-6 flex items-center gap-2 px-5 py-3 rounded-xl w-fit ${darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>
                <FiCheckCircle /> {notification}
              </div>
            )}

            <div className="mb-8">
              <h1 className={`text-4xl font-extrabold ${darkMode ? "text-white" : "text-gray-900"}`}>Settings</h1>
              <p className={`mt-2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Manage your account preferences and application settings.</p>
            </div>

            {/* PROFILE */}
            <SectionCard darkMode={darkMode}>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center text-xl font-bold">{initials}</div>
                <div>
                  <h2 className="font-bold text-lg capitalize">{displayName}</h2>
                  <p className="text-sm text-gray-500">{email}</p>
                </div>
              </div>
            </SectionCard>

            {/* GMAIL CREDENTIALS */}
            <SectionCard darkMode={darkMode}>
              <div className="flex items-center gap-3 mb-5">
                <div className={`p-3 rounded-xl ${darkMode ? "bg-blue-500/20 text-blue-300" : "bg-blue-100 text-blue-600"}`}><FiMail /></div>
                <div>
                  <h2 className="font-semibold">Gmail Sending Account</h2>
                  <p className="text-sm text-gray-500">Required for scheduling and sending emails.</p>
                </div>
              </div>

              {mailbox ? (
                <div className={`flex items-center justify-between p-4 rounded-xl border ${darkMode ? "border-green-500/30 bg-green-500/10" : "bg-green-50 border-green-200"}`}>
                  <div>
                    <p className="text-sm text-gray-500">Connected account</p>
                    <p className={`font-medium ${darkMode ? "text-green-300" : "text-green-700"}`}>{mailbox.gmail_address}</p>
                  </div>
                  <button onClick={removeMailbox} className="text-red-400 hover:text-red-500 text-sm underline">Remove</button>
                </div>
              ) : (
                <form onSubmit={saveMailbox} className="space-y-4">
                  <div>
                    <label className="text-sm text-gray-500 block mb-1">Gmail Address</label>
                    <input type="email" required value={gmailForm.gmail_address}
                      onChange={(e) => setGmailForm({ ...gmailForm, gmail_address: e.target.value })}
                      placeholder="you@gmail.com"
                      className={`w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-200"}`} />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 block mb-1">App Password <span className="text-xs">(16-char, from Google Account → Security → App Passwords)</span></label>
                    <input type="password" required value={gmailForm.app_password}
                      onChange={(e) => setGmailForm({ ...gmailForm, app_password: e.target.value })}
                      placeholder="xxxx xxxx xxxx xxxx"
                      className={`w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-200"}`} />
                  </div>
                  <button type="submit" disabled={gmailLoading}
                    className={`px-6 py-3 rounded-xl text-white font-medium disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
                    {gmailLoading ? "Saving..." : "Save Gmail Credentials"}
                  </button>
                </form>
              )}
            </SectionCard>

            {/* APPEARANCE */}
            <SectionCard darkMode={darkMode}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-purple-100 text-purple-600"><FiMoon /></div>
                  <div>
                    <h2 className="font-semibold">Dark Mode</h2>
                    <p className="text-sm text-gray-500">Enable dark theme across the application.</p>
                  </div>
                </div>
                <button onClick={toggleTheme}
                  className={`w-14 h-7 rounded-full transition relative ${darkMode ? "bg-purple-600" : "bg-gray-300"}`}>
                  <span className={`absolute top-1 w-5 h-5 rounded-full bg-white transition ${darkMode ? "left-8" : "left-1"}`} />
                </button>
              </div>
            </SectionCard>

            {/* NOTIFICATIONS */}
            <SectionCard darkMode={darkMode}>
              <SettingRow icon={<FiBell />} title="Email Notifications" desc="Receive updates about your emails." darkMode={darkMode} />
              <SettingRow icon={<FiShield />} title="Security Alerts" desc="Get notified about account activity." darkMode={darkMode} />
            </SectionCard>

            {/* ACCOUNT */}
            <SectionCard darkMode={darkMode}>
              <h2 className="font-semibold mb-5">Account</h2>
              <button onClick={handleLogout} className="flex items-center gap-3 px-5 py-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition">
                <FiLogOut /> Logout
              </button>
            </SectionCard>
          </div>
        </main>
      </div>
    </div>
  );
}

function SectionCard({ children, darkMode }) {
  return (
    <div className={`p-6 rounded-3xl border mb-6 transition ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200 shadow-sm"}`}>
      {children}
    </div>
  );
}

function SettingRow({ icon, title, desc, darkMode }) {
  return (
    <div className="flex items-center justify-between py-4 border-b last:border-none">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-xl ${darkMode ? "bg-gray-800 text-purple-400" : "bg-gray-100 text-gray-700"}`}>{icon}</div>
        <div>
          <h3 className="font-medium">{title}</h3>
          <p className="text-sm text-gray-500">{desc}</p>
        </div>
      </div>
      <button className="w-11 h-6 rounded-full bg-gray-300 relative">
        <span className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full" />
      </button>
    </div>
  );
}
