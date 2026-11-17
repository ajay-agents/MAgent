import { useEffect, useState } from "react";
import { FiMail } from "react-icons/fi";
import { api } from "../services/api";

// Shown above every app page until the account's email is verified
export default function VerifyBanner({ darkMode }) {
  const [me, setMe]     = useState(null);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/auth/me").then(setMe).catch(() => {});
  }, []);

  if (!me || me.email_verified) return null;

  const resend = async () => {
    setError("");
    try {
      await api.post("/api/auth/resend-verification", {});
      setSent(true);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className={`px-8 py-3 text-sm flex flex-wrap items-center gap-3 border-b ${darkMode ? "bg-amber-500/10 text-amber-200 border-amber-500/20" : "bg-amber-50 text-amber-800 border-amber-200"}`}>
      <FiMail className="shrink-0" />
      <span>Verify your email to start writing and sending. We sent a link to <b>{me.email}</b>.</span>
      {sent ? <span className="font-medium">Sent! Check your inbox.</span> : (
        <button onClick={resend} className="underline font-medium">Resend email</button>
      )}
      {error && <span className="text-red-500">{error}</span>}
    </div>
  );
}
