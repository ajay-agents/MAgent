import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { FiLock, FiCheckCircle } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { AuthCard } from "./VerifyEmail";

export default function ResetPassword() {
  const { darkMode } = useTheme();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [error, setError]       = useState("");
  const [saving, setSaving]     = useState(false);
  const [done, setDone]         = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setSaving(true);
    setError("");
    try {
      const { access_token } = await api.post("/api/auth/reset-password", { token, password });
      login(access_token, null); // store the token so the next call is authenticated
      const me = await api.get("/api/auth/me");
      login(access_token, { email: me.email });
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const field = `w-full p-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-300"}`;

  if (!token) {
    return <AuthCard darkMode={darkMode} title="Link incomplete"><p className="text-gray-500">Open the full link from the email, or <Link to="/" className="underline">request a new one</Link>.</p></AuthCard>;
  }
  if (done) {
    return (
      <AuthCard darkMode={darkMode} title="Password updated" icon={<FiCheckCircle className="text-green-500" />}>
        <p className="text-gray-500 mb-6">You're signed in with your new password.</p>
        <button onClick={() => navigate("/dashboard")} className={`w-full py-3 rounded-xl text-white font-semibold ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
          Go to dashboard
        </button>
      </AuthCard>
    );
  }
  return (
    <AuthCard darkMode={darkMode} title="Choose a new password" icon={<FiLock />}>
      <form onSubmit={submit} className="space-y-4">
        {error && <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}
        <input type="password" placeholder="New password (8+ characters)" value={password} onChange={(e) => setPassword(e.target.value)} className={field} autoFocus />
        <input type="password" placeholder="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={field} />
        <button type="submit" disabled={saving} className={`w-full py-3 rounded-xl text-white font-semibold disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
          {saving ? "Saving..." : "Save password"}
        </button>
      </form>
    </AuthCard>
  );
}
