import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { FiBell, FiMoon, FiShield, FiLogOut, FiMail, FiCheckCircle, FiBriefcase, FiAlertCircle, FiZap, FiSlash } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { useBilling } from "../services/billing";
import UpgradeModal from "../components/UpgradeModal";

// Messages for the ?gmail=...&reason=... the backend redirects to after Google's consent screen
const GOOGLE_RESULT = {
  connected: "Gmail connected. MailFlow can now send emails from your account.",
  denied:    "Gmail wasn't connected because access was cancelled on Google's screen.",
  scope:     "Gmail wasn't connected. Please allow \"Send email on your behalf\" on Google's screen.",
  expired:   "The connection attempt expired. Please try connecting again.",
  google:    "Google couldn't complete the connection. Please try again.",
  invalid:   "Something went wrong connecting Gmail. Please try again.",
};

function initialGoogleNotice(params) {
  const result = params.get("gmail");
  if (result === "connected") return { msg: GOOGLE_RESULT.connected, error: false };
  if (result === "error") return { msg: GOOGLE_RESULT[params.get("reason")] || GOOGLE_RESULT.invalid, error: true };
  return null;
}

export default function Settings() {
  const { darkMode, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [mailbox, setMailbox]         = useState(null);
  const [gmailForm, setGmailForm]     = useState({ gmail_address: "", app_password: "" });
  const [notification, setNotification] = useState(() => initialGoogleNotice(searchParams)); // { msg, error }
  const [options, setOptions]         = useState({ google_oauth: false });
  const [showAppPassword, setShowAppPassword] = useState(false);
  const [connecting, setConnecting]   = useState(false);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [profile, setProfile]         = useState({ full_name: "", role: "", company: "", about: "", signature: "", postal_address: "" });
  const [profileSaving, setProfileSaving] = useState(false);
  const [showPlans, setShowPlans]     = useState(false);
  const billing = useBilling({ fresh: true });

  const notify = (msg, error = false) => { setNotification({ msg, error }); setTimeout(() => setNotification(null), 5000); };

  // Clear the one-time Google result from the URL and auto-hide its message
  useEffect(() => {
    if (!searchParams.has("gmail")) return;
    setSearchParams({}, { replace: true });
    const t = setTimeout(() => setNotification(null), 6000);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    api.get("/api/mailbox/options").then(setOptions).catch(() => {});
    api.get("/api/mailbox").then(setMailbox).catch(() => {});
    api.get("/api/profile")
      .then((p) => setProfile({
        full_name: p.full_name || "", role: p.role || "", company: p.company || "",
        about: p.about || "", signature: p.signature || "", postal_address: p.postal_address || "",
      }))
      .catch(() => {});
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
      notify(err.message || "Failed to save credentials", true);
    } finally {
      setGmailLoading(false);
    }
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    setProfileSaving(true);
    try {
      await api.put("/api/profile", profile);
      notify("Sender profile saved. New emails will use it.");
    } catch (err) {
      notify(err.message || "Failed to save profile", true);
    } finally {
      setProfileSaving(false);
    }
  };

  const removeMailbox = async () => {
    try {
      await api.delete("/api/mailbox");
      setMailbox(null);
      notify("Gmail disconnected");
    } catch (err) {
      notify(err.message, true);
    }
  };

  const connectGoogle = async () => {
    setConnecting(true);
    try {
      const { url } = await api.get("/api/mailbox/google/authorize");
      window.location.assign(url); // Google redirects back to /settings?gmail=...
    } catch (err) {
      notify(err.message || "Couldn't start Google sign-in", true);
      setConnecting(false);
    }
  };

  const email = user?.email || "—";
  const displayName = email.split("@")[0];
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-5xl mx-auto">
            {notification && (
              <div className={`mb-6 flex items-center gap-2 px-5 py-3 rounded-xl w-fit ${
                notification.error
                  ? "bg-red-500/10 text-red-400 border border-red-400/30"
                  : darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"
              }`}>
                {notification.error ? <FiAlertCircle /> : <FiCheckCircle />} {notification.msg}
              </div>
            )}

            <div className="mb-8">
              <h1 className={`text-4xl font-extrabold ${darkMode ? "text-white" : "text-gray-900"}`}>Settings</h1>
              <p className={`mt-2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Manage your account preferences and application settings.</p>
            </div>

            {/* PROFILE */}
            <SectionCard darkMode={darkMode}>
              <div className="flex items-center gap-4 mb-6">
                <div className={`w-14 h-14 rounded-full text-white flex items-center justify-center text-xl font-bold ${
                  darkMode ? "bg-gradient-to-br from-indigo-500 to-purple-600" : "bg-gradient-to-br from-gray-900 to-gray-600"
                }`}>{initial}</div>
                <div>
                  <h2 className="font-bold text-lg capitalize">{displayName}</h2>
                  <p className="text-sm text-gray-500">{email}</p>
                </div>
              </div>
            </SectionCard>

            {/* PLAN & USAGE */}
            {billing && <PlanCard billing={billing} darkMode={darkMode} onUpgrade={() => setShowPlans(true)} />}

            {/* SENDER PROFILE */}
            <SectionCard darkMode={darkMode}>
              <div className="flex items-center gap-3 mb-5">
                <div className={`p-3 rounded-xl ${darkMode ? "bg-purple-500/20 text-purple-300" : "bg-gray-100 text-gray-700"}`}><FiBriefcase /></div>
                <div>
                  <h2 className="font-semibold">Sender Profile</h2>
                  <p className="text-sm text-gray-500">The AI uses this in every email, so it can talk about you accurately instead of guessing.</p>
                </div>
              </div>
              <form onSubmit={saveProfile} className="space-y-4">
                <div className="grid md:grid-cols-3 gap-4">
                  <ProfileField label="Full name" placeholder="Ajay Rajput" maxLength={100} darkMode={darkMode}
                    value={profile.full_name} onChange={(v) => setProfile({ ...profile, full_name: v })} />
                  <ProfileField label="Role" placeholder="Founder" maxLength={100} darkMode={darkMode}
                    value={profile.role} onChange={(v) => setProfile({ ...profile, role: v })} />
                  <ProfileField label="Company" placeholder="Acme Inc." maxLength={150} darkMode={darkMode}
                    value={profile.company} onChange={(v) => setProfile({ ...profile, company: v })} />
                </div>
                <ProfileField label="What you offer" multiline rows={4} maxLength={1500} darkMode={darkMode}
                  placeholder="What your company does, who it's for, and results you can back up (e.g. customers, numbers, case studies)."
                  value={profile.about} onChange={(v) => setProfile({ ...profile, about: v })} />
                <ProfileField label="Email signature" multiline rows={3} maxLength={500} darkMode={darkMode}
                  placeholder={"Ajay Rajput\nFounder, Acme Inc.\nacme.com"}
                  value={profile.signature} onChange={(v) => setProfile({ ...profile, signature: v })} />
                <ProfileField label="Postal address (shown in campaign email footers)" maxLength={300} darkMode={darkMode}
                  placeholder="e.g. 12 MG Road, Indore 452001, India"
                  value={profile.postal_address} onChange={(v) => setProfile({ ...profile, postal_address: v })} />
                <p className="text-xs text-gray-500 -mt-2">
                  US law (CAN-SPAM) requires a physical address in commercial email. A business address or PO box is fine.
                </p>
                <button type="submit" disabled={profileSaving}
                  className={`px-6 py-3 rounded-xl text-white font-medium disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
                  {profileSaving ? "Saving..." : "Save Profile"}
                </button>
              </form>
            </SectionCard>

            {/* DO-NOT-CONTACT LIST */}
            <SuppressionCard darkMode={darkMode} notify={notify} />

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
                    <p className="text-sm text-gray-500">
                      Connected {mailbox.provider === "google" ? "with Google" : "with an App Password"}
                    </p>
                    <p className={`font-medium ${darkMode ? "text-green-300" : "text-green-700"}`}>{mailbox.gmail_address}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    {mailbox.provider !== "google" && options.google_oauth && (
                      <button onClick={connectGoogle} disabled={connecting}
                        className={`text-sm underline disabled:opacity-60 ${darkMode ? "text-indigo-300" : "text-gray-900"}`}>
                        Switch to Google sign-in
                      </button>
                    )}
                    <button onClick={removeMailbox} className="text-red-400 hover:text-red-500 text-sm underline">Disconnect</button>
                  </div>
                </div>
              ) : (
                <>
                  {options.google_oauth && (
                    <div className="space-y-3">
                      <button onClick={connectGoogle} disabled={connecting}
                        className={`w-full md:w-auto px-6 py-3 rounded-xl font-medium flex items-center justify-center gap-3 border transition disabled:opacity-60 ${
                          darkMode ? "bg-white text-gray-900 border-white hover:bg-gray-100" : "bg-white text-gray-900 border-gray-300 hover:bg-gray-50 shadow-sm"
                        }`}>
                        <GoogleLogo /> {connecting ? "Opening Google..." : "Connect with Google"}
                      </button>
                      <p className="text-sm text-gray-500">
                        Recommended. MailFlow only asks for permission to send emails you create here. It can't read your inbox, and you can disconnect anytime.
                      </p>
                      {!showAppPassword && (
                        <button onClick={() => setShowAppPassword(true)} className="text-sm text-gray-500 underline">
                          Use an App Password instead
                        </button>
                      )}
                    </div>
                  )}

                  {(!options.google_oauth || showAppPassword) && (
                    <form onSubmit={saveMailbox} className={`space-y-4 ${options.google_oauth ? `mt-5 pt-5 border-t ${darkMode ? "border-gray-800" : "border-gray-200"}` : ""}`}>
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
                </>
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
      {showPlans && <UpgradeModal darkMode={darkMode} onClose={() => setShowPlans(false)} />}
    </div>
  );
}

function PlanCard({ billing, darkMode, onUpgrade }) {
  const { plan, usage } = billing;
  const pct = Math.min(100, Math.round((usage.ai_emails / plan.ai_emails_per_month) * 100));
  const resets = new Date(usage.resets_at).toLocaleDateString([], { day: "numeric", month: "short" });
  const bar = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900";
  return (
    <SectionCard darkMode={darkMode}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-xl ${darkMode ? "bg-purple-500/20 text-purple-300" : "bg-gray-100 text-gray-700"}`}><FiZap /></div>
          <div>
            <h2 className="font-semibold">{plan.name} plan</h2>
            <p className="text-sm text-gray-500">
              {plan.campaign_recipients.toLocaleString()} recipients per campaign · {plan.followups ? "automatic follow-ups" : "no follow-ups"}
            </p>
          </div>
        </div>
        <button onClick={onUpgrade}
          className={plan.id === "free"
            ? `px-5 py-2.5 rounded-xl text-white font-medium ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`
            : `px-5 py-2.5 rounded-xl border ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
          {plan.id === "free" ? "Upgrade to Pro" : "Compare plans"}
        </button>
      </div>
      <div className="mt-5">
        <div className="flex justify-between text-sm mb-2">
          <span><b>{usage.ai_emails.toLocaleString()}</b> of {plan.ai_emails_per_month.toLocaleString()} AI emails used this month</span>
          <span className="text-gray-500">Resets {resets}</span>
        </div>
        <div className={`h-2 rounded-full overflow-hidden ${darkMode ? "bg-gray-800" : "bg-gray-100"}`}>
          <div className={`h-full ${bar}`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-500 mt-2">Every AI write counts: new emails, rewrites and refinements, campaign emails and follow-ups.</p>
        <p className="text-sm mt-4">
          <b>{usage.emails_sent_24h.toLocaleString()}</b> of {usage.daily_send_limit.toLocaleString()} emails sent in the last 24 hours
          <span className="text-gray-500"> · a safe daily limit for Gmail. Anything over it waits and sends automatically.</span>
        </p>
      </div>
    </SectionCard>
  );
}

function SectionCard({ children, darkMode }) {
  return (
    <div className={`p-6 rounded-3xl border mb-6 transition ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200 shadow-sm"}`}>
      {children}
    </div>
  );
}

function SuppressionCard({ darkMode, notify }) {
  const [items, setItems]   = useState([]);
  const [email, setEmail]   = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.get("/api/suppressions").then(setItems).catch(() => {});
  }, []);

  const add = async (e) => {
    e.preventDefault();
    setAdding(true);
    try {
      await api.post("/api/suppressions", { email });
      setItems(await api.get("/api/suppressions"));
      setEmail("");
      notify(`${email} won't be emailed again`);
    } catch (err) {
      notify(err.message, true);
    } finally {
      setAdding(false);
    }
  };

  const remove = async (item) => {
    const msg = item.reason === "unsubscribed"
      ? `${item.email} unsubscribed themselves. Only remove them if they've asked to hear from you again. Remove?`
      : `Allow emailing ${item.email} again?`;
    if (!window.confirm(msg)) return;
    try {
      await api.delete(`/api/suppressions/${encodeURIComponent(item.email)}`);
      setItems((prev) => prev.filter((i) => i.email !== item.email));
    } catch (err) {
      notify(err.message, true);
    }
  };

  return (
    <SectionCard darkMode={darkMode}>
      <div className="flex items-center gap-3 mb-5">
        <div className={`p-3 rounded-xl ${darkMode ? "bg-red-500/20 text-red-300" : "bg-red-50 text-red-600"}`}><FiSlash /></div>
        <div>
          <h2 className="font-semibold">Do-not-contact list</h2>
          <p className="text-sm text-gray-500">People who unsubscribed, plus anyone you add. MailFlow never emails these addresses and skips them in CSV imports.</p>
        </div>
      </div>
      <form onSubmit={add} className="flex gap-3">
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="someone@example.com"
          className={`flex-1 px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-600" : "bg-white border-gray-200"}`} />
        <button type="submit" disabled={adding}
          className={`px-5 py-3 rounded-xl text-white font-medium disabled:opacity-60 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
          {adding ? "Adding..." : "Add"}
        </button>
      </form>
      {items.length > 0 ? (
        <ul className={`mt-4 divide-y rounded-xl border max-h-64 overflow-y-auto ${darkMode ? "divide-gray-800 border-gray-800" : "divide-gray-100 border-gray-200"}`}>
          {items.map((i) => (
            <li key={i.email} className="flex items-center justify-between px-4 py-3 text-sm">
              <span className="truncate">{i.email}</span>
              <span className="flex items-center gap-4 shrink-0">
                <span className="text-gray-500">{i.reason === "unsubscribed" ? "Unsubscribed" : "Added by you"} · {new Date(i.created_at).toLocaleDateString()}</span>
                <button onClick={() => remove(i)} className="text-gray-500 hover:text-red-500 underline">Remove</button>
              </span>
            </li>
          ))}
        </ul>
      ) : <p className="mt-4 text-sm text-gray-500">No one yet. Everyone who clicks the unsubscribe link in a campaign email appears here automatically.</p>}
    </SectionCard>
  );
}

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
  );
}

function ProfileField({ label, value, onChange, multiline, darkMode, ...props }) {
  const cls = `w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white placeholder:text-gray-600" : "bg-white border-gray-200 placeholder:text-gray-400"}`;
  return (
    <div>
      <label className="text-sm text-gray-500 block mb-1">{label}</label>
      {multiline
        ? <textarea value={value} onChange={(e) => onChange(e.target.value)} className={`${cls} resize-y`} {...props} />
        : <input value={value} onChange={(e) => onChange(e.target.value)} className={cls} {...props} />}
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
