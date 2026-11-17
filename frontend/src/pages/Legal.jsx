import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

// ── Fill these in before launch (and have the text reviewed by a lawyer) ─────
const COMPANY        = "[Company legal name]";
const CONTACT_EMAIL  = "[privacy@yourdomain.com]";
const POSTAL_ADDRESS = "[Registered address]";
const JURISDICTION   = "[Country/state whose law applies]";
const EFFECTIVE_DATE = "[Effective date]";

function LegalShell({ title, children }) {
  const { darkMode } = useTheme();
  return (
    <div className={`min-h-screen ${darkMode ? "bg-[#090B12] text-gray-200" : "bg-gray-50 text-gray-800"}`}>
      <div className="max-w-3xl mx-auto px-4 sm:px-8 py-12">
        <Link to="/" className={`text-sm font-semibold ${darkMode ? "text-gray-400" : "text-gray-500"}`}>← MailFlow AI</Link>
        <h1 className={`text-4xl font-extrabold mt-6 ${darkMode ? "text-white" : "text-gray-900"}`}>{title}</h1>
        <p className="text-sm text-gray-500 mt-2">Effective {EFFECTIVE_DATE}</p>
        <div className={`mt-8 space-y-6 leading-7 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:mt-10 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-1 [&_a]:underline ${darkMode ? "[&_h2]:text-white" : "[&_h2]:text-gray-900"}`}>
          {children}
        </div>
        <p className="mt-12 text-sm text-gray-500">
          <Link to="/privacy" className="underline">Privacy Policy</Link> · <Link to="/terms" className="underline">Terms of Service</Link>
        </p>
      </div>
    </div>
  );
}

export function Privacy() {
  return (
    <LegalShell title="Privacy Policy">
      <p>
        MailFlow AI ("MailFlow", "we") is operated by {COMPANY}. This policy explains what we collect when you use
        MailFlow to write and send email, how we use it, and the choices you have.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><b>Account data:</b> your email address and a hashed (never plain-text) password.</li>
        <li><b>Sender profile:</b> the name, role, company, description, signature and postal address you enter.</li>
        <li><b>Email content and contacts:</b> emails you write or generate, and the recipient names, addresses and notes you type or upload (for example in a CSV). You decide what you upload and are responsible for having a lawful basis to contact those people.</li>
        <li><b>Gmail connection:</b> your Gmail address and either an encrypted Google access token or an encrypted Gmail App Password, used only to send the emails you ask us to send.</li>
        <li><b>Usage and technical data:</b> counts of AI emails and sent emails (for plan limits), and server logs such as IP addresses, kept for security and troubleshooting.</li>
        <li><b>Unsubscribe records:</b> addresses that opted out of your emails, so they are never contacted again.</li>
      </ul>

      <h2>How we use Google user data</h2>
      <p>
        If you choose "Connect with Google", MailFlow requests permission to <b>send email on your behalf</b>
        (<code>gmail.send</code>) and to see your email address. We use this only to send the emails you create, schedule or
        launch in MailFlow. We cannot read your inbox. We do not use Google user data for advertising, do not sell it, and do
        not use it to train AI models. People at MailFlow do not read it unless you ask us to help with a problem, it is needed for
        security, or the law requires it.
      </p>
      <p>
        MailFlow's use and transfer to any other app of information received from Google APIs will adhere to the{" "}
        <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer">
          Google API Services User Data Policy</a>, including the Limited Use requirements.
      </p>

      <h2>AI processing</h2>
      <p>
        To write an email, we send the details you provide (such as purpose, recipient name and context, and your sender
        profile) to an AI provider: OpenAI, Google (Gemini) or Groq, depending on availability. Each provider processes this
        data to return the generated text, under its own API terms. Content you upload is not used to train our own models.
      </p>

      <h2>Sharing</h2>
      <p>
        We share data only with service providers who help run MailFlow (hosting, AI providers, our transactional email
        provider, and Google when you send through Gmail), when the law requires it, or with your consent. We do not sell
        personal data.
      </p>

      <h2>Security and retention</h2>
      <p>
        Gmail credentials and tokens are encrypted at rest, and passwords are hashed. We keep your data while your account is
        open. When you ask us to delete your account, we delete your data within 30 days, except where we must keep
        something by law. Disconnecting Gmail in Settings deletes the stored credential and revokes MailFlow's Google access.
      </p>

      <h2>Your rights</h2>
      <p>
        You can access, correct, export or delete your data, and object to or restrict its processing, by emailing{" "}
        {CONTACT_EMAIL}. If you are in the EU/UK, you may also complain to your data protection authority.
        Recipients of emails sent through MailFlow can unsubscribe using the link in any campaign email.
      </p>

      <h2>Contact</h2>
      <p>{COMPANY}, {POSTAL_ADDRESS}. Email: {CONTACT_EMAIL}.</p>
    </LegalShell>
  );
}

export function Terms() {
  return (
    <LegalShell title="Terms of Service">
      <p>
        These terms govern your use of MailFlow AI, operated by {COMPANY}. By creating an account you agree to them.
      </p>

      <h2>Using MailFlow</h2>
      <ul>
        <li>You must give accurate account information and keep your password secure.</li>
        <li>You are responsible for the emails you send, including AI-generated text. Review emails before sending them: AI can make mistakes.</li>
        <li>You must have a lawful basis to email the people you contact and must comply with anti-spam and privacy laws that apply to you, such as CAN-SPAM, GDPR and India's DPDP Act.</li>
        <li>You must also follow Google's and Gmail's terms and sending limits.</li>
      </ul>

      <h2>Not allowed</h2>
      <ul>
        <li>Spam, purchased or scraped lists where consent is required, phishing, malware or deceptive content.</li>
        <li>Harassment, or illegal, hateful or sexually explicit content.</li>
        <li>Getting around plan limits, sending limits, unsubscribe handling, or the service's security.</li>
      </ul>
      <p>We may suspend accounts that break these rules or put the service or its sending reputation at risk.</p>

      <h2>Plans and limits</h2>
      <p>
        Free and paid plans include the limits shown in the app, which we may change with notice. Paid plans, once offered,
        renew until cancelled. We aim to keep MailFlow available but do not guarantee uninterrupted service.
      </p>

      <h2>Your content</h2>
      <p>
        You own the content and contacts you add. You give us permission to process them only to provide the service,
        as described in the <Link to="/privacy">Privacy Policy</Link>.
      </p>

      <h2>Disclaimers and liability</h2>
      <p>
        MailFlow is provided "as is". To the extent the law allows, {COMPANY} is not liable for indirect or consequential
        losses, or for the content of emails you send. Our total liability is limited to the amount you paid us in the 12
        months before the claim.
      </p>

      <h2>Ending your account</h2>
      <p>
        You can stop using MailFlow at any time and ask us to delete your account at {CONTACT_EMAIL}. We may end access for
        breach of these terms.
      </p>

      <h2>Changes and law</h2>
      <p>
        We will notify you of material changes. These terms are governed by the laws of {JURISDICTION}.
        Contact: {CONTACT_EMAIL}.
      </p>
    </LegalShell>
  );
}
