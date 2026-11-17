import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { FiCheckCircle, FiAlertCircle, FiMail } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

export function AuthCard({ darkMode, title, icon, children }) {
  return (
    <div className={`min-h-screen flex items-center justify-center px-4 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <div className={`w-full max-w-md rounded-3xl border p-8 shadow-2xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}>
        <p className="text-sm font-semibold text-gray-500 mb-6">MailFlow AI</p>
        <h1 className="text-2xl font-bold flex items-center gap-3 mb-3">{icon}{title}</h1>
        {children}
      </div>
    </div>
  );
}

export default function VerifyEmail() {
  const { darkMode } = useTheme();
  const { isAuthenticated } = useAuth();
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState(token ? "working" : "error");
  const [message, setMessage] = useState(token ? "" : "This link is incomplete. Open the full link from the email.");

  useEffect(() => {
    if (!token) return;
    api.post("/api/auth/verify-email", { token })
      .then(() => setState("done"))
      .catch((err) => { setState("error"); setMessage(err.message); });
  }, [token]);

  const button = `inline-block w-full text-center py-3 rounded-xl text-white font-semibold ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`;

  if (state === "working") return <AuthCard darkMode={darkMode} title="Verifying..." icon={<FiMail />} />;
  if (state === "done") {
    return (
      <AuthCard darkMode={darkMode} title="Email verified" icon={<FiCheckCircle className="text-green-500" />}>
        <p className="text-gray-500 mb-6">You're all set. You can now write and send emails.</p>
        <Link to={isAuthenticated ? "/dashboard" : "/"} className={button}>{isAuthenticated ? "Go to dashboard" : "Log in"}</Link>
      </AuthCard>
    );
  }
  return (
    <AuthCard darkMode={darkMode} title="Couldn't verify" icon={<FiAlertCircle className="text-red-400" />}>
      <p className="text-gray-500 mb-6">{message}</p>
      <Link to={isAuthenticated ? "/dashboard" : "/"} className={button}>{isAuthenticated ? "Back to the app" : "Go to MailFlow"}</Link>
    </AuthCard>
  );
}
