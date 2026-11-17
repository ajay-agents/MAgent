import { useState } from "react";
import { FiX, FiMail, FiLock } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

export default function AuthModal({ isOpen, onClose }) {
  const { darkMode } = useTheme();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState("login");
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState("");

  const handleChange = (e) => {
    setError("");
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const reset = () => setFormData({ name: "", email: "", password: "", confirmPassword: "" });

  const switchTab = (t) => { setTab(t); setError(""); setInfo(""); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (tab === "forgot") {
      if (!formData.email) { setError("Enter your email address."); return; }
      setLoading(true);
      try {
        const res = await api.post("/api/auth/forgot-password", { email: formData.email });
        setInfo(res.detail);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (tab === "login") {
      if (!formData.email || !formData.password) { setError("Please fill in all fields."); return; }
      setLoading(true);
      try {
        const data = await api.post("/api/auth/login", { email: formData.email, password: formData.password });
        login(data.access_token, { email: formData.email });
        reset();
        onClose();
        navigate("/dashboard");
      } catch (err) {
        setError(err.message || "Login failed.");
      } finally {
        setLoading(false);
      }
      return;
    }

    // signup
    if (!formData.email || !formData.password || !formData.confirmPassword) { setError("Please fill in all fields."); return; }
    if (formData.password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (formData.password !== formData.confirmPassword) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      await api.post("/api/auth/signup", { email: formData.email, password: formData.password });
      // auto-login after signup
      const data = await api.post("/api/auth/login", { email: formData.email, password: formData.password });
      login(data.access_token, { email: formData.email });
      reset();
      onClose();
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Signup failed.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
      <div className={`w-full max-w-md rounded-2xl shadow-2xl transition ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
        <div className="flex items-start justify-between p-6 pb-2">
          <div>
            <h2 className="text-3xl font-bold">Welcome to MailFlow AI</h2>
            <p className={`mt-2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Sign in to start generating outreach emails.</p>
          </div>
          <button onClick={onClose}><FiX size={22} /></button>
        </div>

        <div className="px-6">
          <div className={`flex rounded-full p-1 ${darkMode ? "bg-[#090B12]" : "bg-gray-100"}`}>
            {["login", "signup"].map((t) => (
              <button key={t} onClick={() => switchTab(t)}
                className={`w-1/2 rounded-full py-2 font-semibold transition ${tab === t ? darkMode ? "bg-[#11141D] shadow text-white" : "bg-white shadow" : darkMode ? "text-gray-400" : "text-gray-500"}`}>
                {t === "login" ? "Login" : "Sign Up"}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-6">
          {error && <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}
          {info && <div className={`rounded-lg px-4 py-3 text-sm ${darkMode ? "bg-green-500/15 text-green-300" : "bg-green-50 text-green-700"}`}>{info}</div>}
          {tab === "forgot" && <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Enter your account email and we'll send you a link to choose a new password.</p>}

          {tab === "signup" && <InputBox label="Full Name" name="name" placeholder="John Doe" value={formData.name} onChange={handleChange} darkMode={darkMode} />}
          <InputBox label="Email" name="email" placeholder="you@company.com" icon={<FiMail />} value={formData.email} onChange={handleChange} darkMode={darkMode} />
          {tab !== "forgot" && <InputBox label="Password" name="password" placeholder="••••••••" type="password" icon={<FiLock />} value={formData.password} onChange={handleChange} darkMode={darkMode} />}
          {tab === "login" && (
            <button type="button" onClick={() => switchTab("forgot")} className={`-mt-2 text-sm underline ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
              Forgot password?
            </button>
          )}
          {tab === "signup" && <InputBox label="Confirm Password" name="confirmPassword" placeholder="••••••••" type="password" icon={<FiLock />} value={formData.confirmPassword} onChange={handleChange} darkMode={darkMode} />}

          <button type="submit" disabled={loading}
            className={`w-full rounded-xl py-3 font-semibold text-white transition hover:scale-[1.02] disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" : "bg-gray-900 hover:bg-black"}`}>
            {loading ? "Please wait..." : tab === "login" ? "Log in" : tab === "forgot" ? "Send reset link" : "Create Account"}
          </button>
          {tab === "forgot" && (
            <button type="button" onClick={() => switchTab("login")} className={`w-full text-sm underline ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
              Back to log in
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

function InputBox({ label, name, placeholder, icon, type = "text", value, onChange, darkMode }) {
  return (
    <div>
      <label className="font-medium">{label}</label>
      <div className={`mt-2 flex items-center rounded-xl border px-3 transition ${darkMode ? "bg-[#090B12] border-gray-700" : "bg-white border-gray-300"}`}>
        {icon && <span className="text-gray-400">{icon}</span>}
        <input type={type} name={name} placeholder={placeholder} value={value} onChange={onChange}
          className={`w-full p-3 outline-none bg-transparent ${darkMode ? "text-white placeholder:text-gray-500" : "text-gray-900"}`} />
      </div>
    </div>
  );
}
