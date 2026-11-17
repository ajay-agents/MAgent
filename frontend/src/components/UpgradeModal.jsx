import { FiCheck, FiMinus, FiX, FiMail } from "react-icons/fi";
import { useBilling } from "../services/billing";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  // Numeric rows read "<value> <label>", so their labels start lower-case where grammar needs it
  ["AI emails per month", (p) => p.ai_emails_per_month.toLocaleString()],
  ["recipients per campaign", (p) => p.campaign_recipients.toLocaleString()],
  ["Automatic follow-ups", (p) => p.followups],
  ["Sender profile, editing & refine", () => true],
  ["Gmail sending & scheduling", () => true],
];

export default function UpgradeModal({ darkMode, onClose }) {
  const billing = useBilling();
  const { user } = useAuth();

  const mailto = billing?.support_email
    ? `mailto:${billing.support_email}?subject=${encodeURIComponent("Upgrade to MailFlow Pro")}` +
      `&body=${encodeURIComponent(`Hi, I'd like to upgrade my account (${user?.email || ""}) to Pro.`)}`
    : null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className={`w-[640px] max-h-[90vh] overflow-y-auto rounded-3xl p-6 shadow-2xl ${darkMode ? "bg-[#11141D] text-white" : "bg-white text-gray-900"}`}>
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold">Plans</h2>
          <button onClick={onClose}><FiX size={24} /></button>
        </div>

        {!billing ? <p className="mt-6 text-gray-500">Loading...</p> : (
          <>
            <div className="mt-6 grid grid-cols-2 gap-4">
              {billing.plans.map((p) => {
                const current = p.id === billing.plan.id;
                const highlight = p.id === "pro";
                return (
                  <div key={p.id} className={`rounded-2xl border p-5 ${
                    highlight
                      ? darkMode ? "border-indigo-500 bg-indigo-500/5" : "border-gray-900"
                      : darkMode ? "border-gray-700" : "border-gray-200"
                  }`}>
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-bold">{p.name}</h3>
                      {current && <span className={`text-xs px-2 py-0.5 rounded-full ${darkMode ? "bg-gray-700 text-gray-200" : "bg-gray-100 text-gray-600"}`}>Current</span>}
                    </div>
                    <p className="text-2xl font-extrabold mt-1">{p.price_label}</p>
                    <ul className="mt-4 space-y-2 text-sm">
                      {FEATURES.map(([label, get]) => {
                        const v = get(p);
                        return (
                          <li key={label} className="flex items-start gap-2">
                            {v === false ? <FiMinus className="mt-0.5 text-gray-400 shrink-0" /> : <FiCheck className="mt-0.5 text-green-500 shrink-0" />}
                            <span className={v === false ? "text-gray-400" : ""}>
                              {typeof v === "string" ? <><b>{v}</b> {label}</> : label}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
            </div>

            {billing.plan.id !== "pro" && (
              <div className={`mt-6 rounded-2xl p-5 ${darkMode ? "bg-[#090B12]" : "bg-gray-50"}`}>
                <p className="font-semibold">Online payment is coming soon</p>
                <p className="text-sm text-gray-500 mt-1">
                  {mailto ? "Want Pro now? Email us and we'll upgrade your account right away." : "Want Pro now? Contact the MailFlow team and we'll upgrade your account."}
                </p>
                {mailto && (
                  <a href={mailto}
                    className={`mt-4 inline-flex px-5 py-3 rounded-xl text-white items-center gap-2 ${darkMode ? "bg-gradient-to-r from-indigo-500 to-purple-600" : "bg-gray-900 hover:bg-black"}`}>
                    <FiMail /> Email us to upgrade
                  </a>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
