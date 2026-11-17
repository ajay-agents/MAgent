import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import { useTheme } from "../context/ThemeContext";
import { api } from "../services/api";
import { useBilling } from "../services/billing";
import UpgradeModal from "../components/UpgradeModal";
import { CampaignStatusBadge, RecipientStatusBadge } from "../components/CampaignBits";
import {
  FiArrowLeft, FiUpload, FiPlay, FiPause, FiTrash2, FiX, FiCheckCircle, FiAlertCircle,
  FiCornerUpLeft, FiSave, FiRefreshCw, FiDownload,
} from "react-icons/fi";
import { HiSparkles } from "react-icons/hi2";

const SAMPLE_CSV = "email,first name,last name,company,title,notes\n" +
  "priya@example.com,Priya,Shah,FinCo,Head of Data,Just launched a fraud-detection API\n" +
  "rahul@example.com,Rahul,Verma,TeachTube,Founder,Runs a JEE physics YouTube channel\n";

const fmt = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "");
const UNSENT = ["draft", "pending", "failed"];

export default function CampaignDetail() {
  const { id } = useParams();
  const { darkMode } = useTheme();
  const navigate = useNavigate();
  const fileRef = useRef(null);

  const [campaign, setCampaign]     = useState(null);
  const [recipients, setRecipients] = useState([]);
  const [notice, setNotice]         = useState(null); // { msg, error, limit }
  const [showPlans, setShowPlans]   = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [busy, setBusy]             = useState("");
  const [showLaunch, setShowLaunch] = useState(false);
  const [openEmail, setOpenEmail]   = useState(null); // { recipient, emailId }
  const [notFound, setNotFound]     = useState(false);

  const notify = (msg, error = false, limit = false) => {
    setNotice({ msg, error, limit });
    setTimeout(() => setNotice(null), limit ? 12000 : 5000);
  };

  const load = useCallback(async () => {
    try {
      const [c, r] = await Promise.all([api.get(`/api/campaigns/${id}`), api.get(`/api/campaigns/${id}/recipients`)]);
      setCampaign(c);
      setRecipients(r);
    } catch {
      setNotFound(true);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]); // eslint-disable-line react-hooks/set-state-in-effect

  // Live progress while emails are being written or sent
  const active = campaign && (campaign.stats.queued > 0 || campaign.status === "running");
  useEffect(() => {
    if (!active) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [active, load]);

  const run = async (label, fn, success) => {
    setBusy(label);
    try {
      await fn();
      if (success) notify(success);
      await load();
    } catch (err) {
      notify(err.message, true, err.status === 402);
    } finally {
      setBusy("");
    }
  };

  const importCsv = async (file) => {
    if (!file) return;
    const text = await file.text();
    fileRef.current.value = "";
    await run("import", async () => {
      const res = await api.post(`/api/campaigns/${id}/recipients/csv`, { csv: text });
      setImportResult(res);
    });
  };

  const deleteCampaign = () => {
    if (!window.confirm("Delete this campaign? Emails that haven't been sent yet are removed. Sent emails stay in Sent.")) return;
    run("delete", async () => { await api.delete(`/api/campaigns/${id}`); navigate("/campaigns"); });
  };

  if (notFound) {
    return <Shell darkMode={darkMode}><p className="text-gray-500">Campaign not found. <Link to="/campaigns" className="underline">Back to campaigns</Link></p></Shell>;
  }
  if (!campaign) return <Shell darkMode={darkMode}><p className="text-gray-500">Loading...</p></Shell>;

  const s = campaign.stats;
  const isDraft = campaign.status === "draft";
  const card = `rounded-3xl border shadow-xl ${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`;
  const primary = `px-5 py-3 rounded-xl text-white flex items-center gap-2 disabled:opacity-50 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`;
  const secondary = `px-5 py-3 rounded-xl border flex items-center gap-2 disabled:opacity-50 ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`;
  const written = s.recipients - s.new - s.queued - s.error - s.unsubscribed;

  return (
    <Shell darkMode={darkMode}>
      {notice && (
        <div className={`mb-5 px-5 py-3 rounded-xl w-fit flex items-center gap-2 ${notice.error ? "bg-red-500/10 text-red-400 border border-red-400/30" : darkMode ? "bg-green-500/20 text-green-300" : "bg-green-100 text-green-700"}`}>
          {notice.error ? <FiAlertCircle /> : <FiCheckCircle />} {notice.msg}
          {notice.limit && (
            <button onClick={() => setShowPlans(true)} className={`ml-2 shrink-0 px-3 py-1 rounded-lg text-sm text-white ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}>
              See plans
            </button>
          )}
        </div>
      )}

      <Link to="/campaigns" className="text-sm text-gray-500 flex items-center gap-1 mb-3 hover:underline"><FiArrowLeft /> All campaigns</Link>
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-extrabold">{campaign.name}</h1>
            <CampaignStatusBadge status={campaign.status} darkMode={darkMode} />
          </div>
          <p className="mt-2 text-gray-500 capitalize">
            {campaign.purpose.replace(/_/g, " ")} · {campaign.tone} · {campaign.length}
            {campaign.status !== "draft" && (
              <span className="normal-case"> · one email every {campaign.send_interval_minutes} min
                {campaign.followup_count > 0 && ` · ${campaign.followup_count} follow-up${campaign.followup_count > 1 ? "s" : ""}, ${campaign.followup_delay_days} days apart`}</span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {isDraft && (
            <>
              <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => importCsv(e.target.files[0])} />
              <button onClick={() => fileRef.current.click()} disabled={!!busy} className={secondary}>
                <FiUpload /> {busy === "import" ? "Importing..." : "Import CSV"}
              </button>
              {(s.new > 0 || s.error > 0) && (
                <button onClick={() => run("generate", () => api.post(`/api/campaigns/${id}/generate`, {}), "Writing emails in the background...")}
                  disabled={!!busy} className={secondary}>
                  <HiSparkles /> Write {s.new + s.error} email{s.new + s.error === 1 ? "" : "s"}
                </button>
              )}
              <button onClick={() => setShowLaunch(true)} disabled={!!busy || !s.ready || s.queued > 0} className={primary}
                title={s.queued ? "Wait until all emails are written" : !s.ready ? "Write emails first" : ""}>
                <FiPlay /> Launch
              </button>
            </>
          )}
          {campaign.status === "running" && (
            <button onClick={() => run("pause", () => api.post(`/api/campaigns/${id}/pause`, {}), "Campaign paused")} disabled={!!busy} className={secondary}>
              <FiPause /> Pause
            </button>
          )}
          {campaign.status === "paused" && (
            <button onClick={() => run("resume", () => api.post(`/api/campaigns/${id}/resume`, {}), "Campaign resumed")} disabled={!!busy} className={primary}>
              <FiPlay /> Resume
            </button>
          )}
          <button onClick={deleteCampaign} disabled={!!busy} className="px-4 py-3 rounded-xl text-red-500 border border-red-400/40 hover:bg-red-500/10 flex items-center gap-2">
            <FiTrash2 />
          </button>
        </div>
      </div>

      {/* PROGRESS / STATS */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
        {[["Recipients", s.recipients], ["Emails written", written], ["Emails sent", s.emails_sent], ["Replied", s.replied],
          ["Unsubscribed", s.unsubscribed], ["Failed", s.failed + s.error]].map(([label, value]) => (
          <div key={label} className={`${card} p-5`}>
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>

      {s.queued > 0 && (
        <div className={`${card} p-5 mb-6`}>
          <div className="flex justify-between text-sm mb-2">
            <span className="flex items-center gap-2"><FiRefreshCw className="animate-spin" /> Writing personalised emails... {written} of {written + s.queued}</span>
            <span className="text-gray-500">You can leave this page. Writing continues in the background.</span>
          </div>
          <div className={`h-2 rounded-full overflow-hidden ${darkMode ? "bg-gray-800" : "bg-gray-100"}`}>
            <div className={`h-full transition-all ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900"}`}
              style={{ width: `${Math.round((written / Math.max(written + s.queued, 1)) * 100)}%` }} />
          </div>
        </div>
      )}

      {importResult && (
        <div className={`${card} p-5 mb-6`}>
          <div className="flex justify-between items-start">
            <p className="font-medium">
              Added {importResult.added} recipient{importResult.added === 1 ? "" : "s"}
              {importResult.skipped.length > 0 && <span className="text-gray-500 font-normal">, skipped {importResult.skipped.length}</span>}
            </p>
            <button onClick={() => setImportResult(null)}><FiX /></button>
          </div>
          {importResult.skipped.length > 0 && (
            <ul className="mt-2 text-sm text-gray-500 list-disc pl-5 max-h-32 overflow-y-auto">
              {importResult.skipped.map((sk, i) => <li key={i}>{sk.row ? `Row ${sk.row}: ` : ""}{sk.reason}</li>)}
            </ul>
          )}
        </div>
      )}

      {/* RECIPIENTS */}
      {recipients.length === 0 ? (
        <div className={`${card} p-12 text-center`}>
          <FiUpload size={45} className="mx-auto mb-4 text-gray-400" />
          <h2 className="text-xl font-bold">Add recipients from a CSV</h2>
          <p className="mt-2 text-gray-500 max-w-lg mx-auto">
            Needs an <b>email</b> column. Optional: <b>name</b> (or first/last name), <b>company</b>, <b>title</b>, and <b>notes</b>.
            Notes are the best place for personal details the AI should use, like something they posted, launched or said.
          </p>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`} download="mailflow-sample.csv"
            className="mt-4 inline-flex items-center gap-2 text-sm underline text-gray-500"><FiDownload /> Download a sample CSV</a>
        </div>
      ) : (
        <div className={`${card} overflow-hidden`}>
          <div className={`grid grid-cols-12 px-6 py-3 text-xs font-medium uppercase tracking-wide text-gray-500 border-b ${darkMode ? "border-gray-800" : "border-gray-200"}`}>
            <div className="col-span-3">Recipient</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-5">Email</div>
            <div className="col-span-2 text-right">Actions</div>
          </div>
          {recipients.map((r) => {
            const latest = r.emails[r.emails.length - 1];
            const canMarkReplied = ["scheduled", "contacted", "completed", "failed"].includes(r.status);
            return (
              <div key={r.id} className={`grid grid-cols-12 px-6 py-4 items-center border-b last:border-none ${darkMode ? "border-gray-800 hover:bg-[#151923]" : "border-gray-100 hover:bg-gray-50"}`}>
                <div className="col-span-3 min-w-0">
                  <p className="font-medium truncate">{r.name}</p>
                  <p className="text-sm text-gray-500 truncate">{r.email}{r.company ? ` · ${r.company}` : ""}</p>
                </div>
                <div className="col-span-2">
                  <RecipientStatusBadge status={r.status} darkMode={darkMode} />
                  {r.error_message && <p className="text-xs text-red-400 mt-1 pr-2">{r.error_message}</p>}
                </div>
                <div className="col-span-5 min-w-0 pr-4">
                  {latest ? (
                    <button onClick={() => setOpenEmail({ recipient: r, emailId: latest.id })} className="text-left w-full group">
                      <p className="truncate group-hover:underline">{latest.subject}</p>
                      <p className="text-xs text-gray-500">
                        {r.emails.length > 1 && `Step ${latest.step + 1} of ${r.emails.length} · `}
                        {latest.status === "sent" ? `Sent ${fmt(latest.sent_at)}`
                          : latest.status === "pending" ? `Sends ${fmt(latest.scheduled_at)}`
                          : latest.status === "draft" ? "Click to review or edit"
                          : latest.status}
                      </p>
                    </button>
                  ) : <span className="text-sm text-gray-500">—</span>}
                </div>
                <div className="col-span-2 flex justify-end gap-2">
                  {canMarkReplied && (
                    <button title="They replied: stop follow-ups"
                      onClick={() => run(`replied-${r.id}`, () => api.post(`/api/campaigns/${id}/recipients/${r.id}/replied`, {}), `${r.name} marked as replied. Follow-ups stopped.`)}
                      className={`p-2 rounded-lg border text-sm ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                      <FiCornerUpLeft />
                    </button>
                  )}
                  <button title="Remove recipient"
                    onClick={() => window.confirm(`Remove ${r.name}? Unsent emails to them are deleted.`) && run(`remove-${r.id}`, () => api.delete(`/api/campaigns/${id}/recipients/${r.id}`))}
                    className="p-2 rounded-lg border border-red-400/40 text-red-500 hover:bg-red-500/10">
                    <FiTrash2 />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showLaunch && <LaunchModal darkMode={darkMode} campaign={campaign} onClose={() => setShowLaunch(false)}
        onLaunch={(payload) => run("launch", async () => { await api.post(`/api/campaigns/${id}/launch`, payload); setShowLaunch(false); }, "Campaign launched")} />}

      {showPlans && <UpgradeModal darkMode={darkMode} onClose={() => setShowPlans(false)} />}

      {openEmail && <EmailModal darkMode={darkMode} {...openEmail} onClose={() => setOpenEmail(null)} onSaved={load} />}
    </Shell>
  );
}

function Shell({ darkMode, children }) {
  return (
    <div className={`flex h-screen transition-all duration-500 ${darkMode ? "bg-[#090B12] text-white" : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"}`}>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>
    </div>
  );
}

function LaunchModal({ darkMode, campaign, onClose, onLaunch }) {
  const [when, setWhen]       = useState("now");
  const [date, setDate]       = useState("");
  const [time, setTime]       = useState("");
  const [interval, setInterval_] = useState(3);
  const billing = useBilling();
  const canFollowUp = billing?.plan.followups ?? true;
  const [followups, setFollowups] = useState(1);
  const [delay, setDelay]     = useState(3);
  const [error, setError]     = useState("");

  const n = campaign.stats.ready;
  const field = `mt-1 w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white" : "bg-white border-gray-200"}`;
  const totalMinutes = Math.max(n - 1, 0) * interval;
  const duration = totalMinutes < 60 ? `${totalMinutes} min` : `${Math.floor(totalMinutes / 60)} h ${totalMinutes % 60} min`;

  const submit = () => {
    let start_at = null;
    if (when === "later") {
      if (!date || !time) { setError("Pick a date and time."); return; }
      start_at = new Date(`${date}T${time}:00`).toISOString();
    }
    onLaunch({ start_at, send_interval_minutes: Number(interval), followup_count: canFollowUp ? Number(followups) : 0,
      followup_delay_days: Number(delay) });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className={`w-[480px] rounded-3xl p-6 shadow-2xl ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold">Launch campaign</h2>
          <button onClick={onClose}><FiX size={22} /></button>
        </div>
        <p className="text-sm text-gray-500 mt-1">{n} email{n === 1 ? "" : "s"} ready to send.</p>

        <div className="mt-5 space-y-4">
          <div>
            <label className="text-sm text-gray-500">Start</label>
            <div className="mt-1 flex gap-2">
              {[["now", "Now"], ["later", "Pick a time"]].map(([v, l]) => (
                <button key={v} onClick={() => setWhen(v)}
                  className={`flex-1 py-2 rounded-xl border text-sm ${when === v ? (darkMode ? "border-indigo-500 bg-indigo-500/10" : "border-gray-900 bg-gray-100") : darkMode ? "border-gray-700" : "border-gray-200"}`}>{l}</button>
              ))}
            </div>
            {when === "later" && (
              <div className="grid grid-cols-2 gap-2 mt-2">
                <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={field} />
                <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className={field} />
              </div>
            )}
          </div>
          <div>
            <label className="text-sm text-gray-500">Minutes between emails</label>
            <input type="number" min={1} max={240} value={interval} onChange={(e) => setInterval_(e.target.value)} className={field} />
            <p className="text-xs text-gray-500 mt-1">Spacing emails out looks natural and protects your Gmail reputation. All {n} go out over about {duration}.</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-gray-500">Follow-ups if no reply</label>
              <select value={canFollowUp ? followups : 0} disabled={!canFollowUp} onChange={(e) => setFollowups(e.target.value)} className={`${field} disabled:opacity-50`}>
                {[0, 1, 2, 3].map((v) => <option key={v} value={v}>{v === 0 ? "None" : v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-500">Days between</label>
              <input type="number" min={1} max={30} value={delay} disabled={!canFollowUp || Number(followups) === 0} onChange={(e) => setDelay(e.target.value)} className={`${field} disabled:opacity-50`} />
            </div>
          </div>
          {billing && n > billing.usage.daily_send_limit - billing.usage.emails_sent_24h && (
            <p className={`text-xs rounded-lg px-3 py-2 ${darkMode ? "bg-amber-500/10 text-amber-300" : "bg-amber-50 text-amber-700"}`}>
              You can send {Math.max(billing.usage.daily_send_limit - billing.usage.emails_sent_24h, 0)} more emails in the next 24 hours
              (Gmail&apos;s safe daily limit is {billing.usage.daily_send_limit}). The rest will wait and go out automatically over the following days.
            </p>
          )}
          <p className="text-xs text-gray-500">
            Every email gets an unsubscribe link at the bottom (required by law and by Gmail). People who unsubscribe are never emailed again.
          </p>
          {!canFollowUp && (
            <p className="text-xs text-gray-500">Automatic follow-ups are part of the Pro plan. Upgrade in Settings → Plan.</p>
          )}
          {canFollowUp && Number(followups) > 0 && (
            <p className="text-xs text-gray-500">
              Follow-ups are written by AI after each send and go out in the same Gmail thread. When someone answers, click
              <FiCornerUpLeft className="inline mx-1" /> on their row to stop their follow-ups.
            </p>
          )}
        </div>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
        <button onClick={submit}
          className={`mt-6 w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
          <FiPlay /> Launch
        </button>
      </div>
    </div>
  );
}

function EmailModal({ darkMode, recipient, emailId, onClose, onSaved }) {
  const [activeId, setActiveId] = useState(emailId);
  const [email, setEmail]       = useState(null);
  const [edit, setEdit]         = useState({ subject: "", body: "" });
  const [busy, setBusy]         = useState("");
  const [error, setError]       = useState("");

  useEffect(() => {
    api.get(`/api/emails/${activeId}`)
      .then((e) => { setEmail(e); setEdit({ subject: e.subject, body: e.body }); })
      .catch((err) => setError(err.message));
  }, [activeId]);

  const editable = email && UNSENT.includes(email.status);
  const dirty = email && (edit.subject !== email.subject || edit.body !== email.body);
  const field = `w-full px-4 py-3 rounded-xl border outline-none ${darkMode ? "bg-[#090B12] border-gray-700 text-white focus:border-indigo-500" : "bg-white border-gray-200 focus:border-gray-900"} disabled:opacity-80`;

  const act = async (label, fn) => {
    setBusy(label);
    setError("");
    try {
      const updated = await fn();
      setEmail(updated);
      setEdit({ subject: updated.subject, body: updated.body });
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  };

  const close = () => { if (!dirty || window.confirm("Discard your unsaved changes?")) onClose(); };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className={`w-[640px] max-h-[90vh] overflow-y-auto rounded-3xl p-6 shadow-2xl ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-2xl font-bold">{recipient.name}</h2>
          <button onClick={close}><FiX size={24} /></button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{recipient.email}</p>

        {recipient.emails.length > 1 && (
          <div className="flex gap-2 mb-4">
            {recipient.emails.map((e) => (
              <button key={e.id} onClick={() => !dirty && setActiveId(e.id)} disabled={dirty && e.id !== activeId}
                className={`px-3 py-1.5 rounded-full border text-sm ${e.id === activeId ? (darkMode ? "border-indigo-500 text-white" : "border-gray-900") : darkMode ? "border-gray-700 text-gray-400" : "border-gray-200 text-gray-500"}`}>
                {e.step === 0 ? "First email" : `Follow-up ${e.step}`}
              </button>
            ))}
          </div>
        )}

        {!email ? <p className="text-gray-500">{error || "Loading..."}</p> : (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {email.status === "sent" ? `Sent ${fmt(email.sent_at)}` : email.status === "pending" ? `Scheduled for ${fmt(email.scheduled_at)}` : `Status: ${email.status}`}
              {email.error_message && <span className="text-red-400"> · {email.error_message}</span>}
            </p>
            <label className="text-sm font-semibold text-gray-500 block mb-1">Subject</label>
            <input value={edit.subject} disabled={!editable} maxLength={300} onChange={(e) => setEdit({ ...edit, subject: e.target.value })} className={`${field} mb-4 font-medium`} />
            <label className="text-sm font-semibold text-gray-500 block mb-1">Body</label>
            <textarea value={edit.body} disabled={!editable} rows={12} onChange={(e) => setEdit({ ...edit, body: e.target.value })} className={`${field} resize-y leading-relaxed`} />
            {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
            {editable && (
              <div className="mt-5 flex justify-between">
                <button onClick={() => (!dirty || window.confirm("Rewriting replaces your edits. Continue?")) && act("regen", () => api.post(`/api/emails/${activeId}/regenerate`, {}))}
                  disabled={!!busy}
                  className={`px-5 py-3 rounded-xl border flex items-center gap-2 disabled:opacity-50 ${darkMode ? "border-gray-700 hover:bg-gray-800" : "border-gray-200 hover:bg-gray-100"}`}>
                  <FiRefreshCw className={busy === "regen" ? "animate-spin" : ""} /> {busy === "regen" ? "Rewriting..." : "Rewrite"}
                </button>
                <button onClick={() => {
                    if (!edit.subject.trim() || !edit.body.trim()) { setError("Subject and body can't be empty."); return; }
                    act("save", () => api.patch(`/api/emails/${activeId}`, edit));
                  }}
                  disabled={!dirty || !!busy}
                  className={`px-5 py-3 rounded-xl text-white flex items-center gap-2 disabled:opacity-50 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
                  <FiSave /> {busy === "save" ? "Saving..." : "Save"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
