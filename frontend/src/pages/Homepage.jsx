import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import {
  FiMail,
  FiMoon,
  FiSun,
  FiArrowRight,
  FiCalendar,
  FiSend,
  FiBriefcase,
} from "react-icons/fi";

export default function Home({ setAuthOpen }) {
  const { darkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();

  return (
    <div
      className={`min-h-screen transition-all duration-500 ${
        darkMode
          ? "bg-[#090B12] text-white"
          : "bg-gradient-to-b from-white via-gray-50 to-white text-gray-900"
      }`}
    >
      {/* NAVBAR */}
      <nav
        className={`border-b backdrop-blur transition ${
          darkMode
            ? "bg-[#090B12]/90 border-gray-800"
            : "bg-white/70 border-gray-200"
        }`}
      >
        <div className="max-w-7xl mx-auto h-16 px-8 flex items-center justify-between">
          <div className="flex items-center gap-3 font-bold text-lg">
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                darkMode
                  ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30"
                  : "bg-gray-900 text-white"
              }`}
            >
              <FiMail size={16} />
            </div>
            MailFlow AI
          </div>

          <div className="flex items-center gap-5">
            <button
              onClick={toggleTheme}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all duration-300 ${
                darkMode
                  ? "bg-gradient-to-br from-gray-800 to-gray-900 hover:from-gray-700 hover:to-gray-800 text-yellow-300 border border-gray-700"
                  : "bg-gray-100 hover:bg-gray-200 text-gray-700"
              }`}
            >
              {darkMode ? <FiSun /> : <FiMoon />}
            </button>

            <button
              onClick={() => setAuthOpen(true)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition
${
  darkMode
    ? "bg-gradient-to-r from-indigo-500 to-purple-500 to-blue-500 hover:scale-105 text-white shadow-lg shadow-purple-500/30"
    : "bg-gray-900 hover:bg-black text-white"
}`}
            >
              Create Email
            </button>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="max-w-7xl mx-auto px-8 py-28 grid lg:grid-cols-2 gap-20 items-center">
        {/* LEFT */}
        <div>
          <div
            className={`inline-flex items-center gap-2 border px-4 py-2 rounded-full text-sm
${
  darkMode
    ? "bg-[#111522] border-gray-700 text-gray-300"
    : "bg-white border-gray-200 text-gray-600"
}`}
          >
            ✨ AI-powered outreach engine
          </div>

          <h1
            className={`text-6xl font-extrabold leading-[1.1] ${
              darkMode ? "text-white" : "text-gray-900"
            }`}
          >
            Generate <br />
            <span
              className={`${
                darkMode
                  ? "bg-gradient-to-r from-violet-400 via-purple-500 to-indigo-400 bg-clip-text text-transparent"
                  : "text-black"
              }`}
            >
              personalized AI
            </span>
            <br />
            outreach emails <br />
            in seconds.
          </h1>
          <p
            className={`mt-8 text-lg leading-8 max-w-xl ${
              darkMode ? "text-gray-400" : "text-gray-600"
            }`}
          >
            Create, preview, send and schedule professional AI-generated emails
            with a clean, focused and distraction-free workflow.
          </p>

          <div className="mt-10 flex gap-5">
            <button
              onClick={() => setAuthOpen(true)}
              className={`group flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300
  ${
    darkMode
      ? "bg-gradient-to-r from-indigo-500 to-purple-500 to-blue-500 hover:scale-105 text-white shadow-lg shadow-purple-500/30"
      : "bg-gray-900 hover:bg-black text-white shadow-md"
  }`}
            >
              <span>Create Email</span>

              <FiArrowRight
                size={16}
                className="transition-transform duration-300 group-hover:translate-x-1"
              />
            </button>

            <button
              onClick={() =>
                document.getElementById("features")?.scrollIntoView({
                  behavior: "smooth",
                })
              }
              className={`px-7 py-4 rounded-xl border transition ${
                darkMode
                  ? "border-gray-700 text-gray-300 hover:bg-gray-800"
                  : "border-gray-300 hover:bg-gray-100"
              }`}
            >
              See how it works
            </button>
          </div>
        </div>

        {/* RIGHT EMAIL CARD */}
        <div className="relative">
          {/* glow background */}
          <div
            className={`absolute -inset-6 blur-3xl rounded-3xl ${
              darkMode
                ? "bg-gradient-to-tr from-indigo-500/20 via-purple-500/20 to-blue-500/20"
                : "bg-gradient-to-tr from-gray-200 to-white opacity-60"
            }`}
          ></div>

          <div
            className={`relative rounded-3xl border shadow-2xl overflow-hidden transition
${darkMode ? "bg-[#11141D] border-gray-800" : "bg-white border-gray-200"}`}
          >
            <div
              className={`border-b px-6 py-4 flex justify-between
${darkMode ? "bg-[#151923] border-gray-800" : "bg-gray-50"}`}
            >
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-300"></div>
                <div className="w-3 h-3 rounded-full bg-gray-300"></div>
                <div className="w-3 h-3 rounded-full bg-gray-300"></div>
              </div>

              <span className="text-sm text-gray-500">AI Draft</span>
            </div>

            <div className="p-7 space-y-4 text-sm">
              <div className="flex">
                <span className="w-20 text-gray-500">To</span>
                <span>sarah@acme.co</span>
              </div>

              <div className="flex">
                <span className="w-20 text-gray-500">Subject</span>
                <span>Partnership opportunity with Acme</span>
              </div>

              <hr />

              <p className="font-medium">Hi Sarah,</p>

              <p className="text-gray-600 leading-7">
                I've been following Acme's work on developer tooling and love
                how you're approaching workflow automation. I'd love to explore
                a partnership around AI-driven outreach...
              </p>

              <div className="space-y-2 pt-4">
                <div className="h-2 bg-gray-200 rounded-full"></div>
                <div className="h-2 bg-gray-200 rounded-full w-4/5"></div>
                <div className="h-2 bg-gray-200 rounded-full w-3/5"></div>
              </div>
            </div>

            <div
              className={`border-t px-6 py-5 flex justify-between items-center ${
                darkMode
                  ? "bg-[#151923] border-gray-800"
                  : "bg-white border-gray-200"
              }`}
            >
              <div className="flex gap-3">
                <button
                  className={`px-5 py-2 rounded-xl text-white transition ${
                    darkMode
                      ? "bg-gradient-to-r from-indigo-500 to-purple-600 hover:shadow-lg hover:shadow-purple-500/30"
                      : "bg-gray-900 hover:bg-black"
                  }`}
                >
                  Send now
                </button>

                <button
                  className={`px-5 py-2 rounded-xl border transition ${
                    darkMode
                      ? "border-purple-500/30 text-gray-300 hover:bg-purple-500/10 hover:border-purple-400"
                      : "border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  Schedule
                </button>
              </div>

              <span className="text-gray-400 text-sm">
                ✨ Generated with AI
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="max-w-7xl mx-auto px-8 py-20">
        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard
            darkMode={darkMode}
            icon={<FiBriefcase />}
            title="AI Email Generation"
            desc="Generate personalized outreach emails tailored to tone, intent and audience."
          />

          <FeatureCard
            darkMode={darkMode}
            icon={<FiSend />}
            title="Instant Send"
            desc="Review and send AI-generated drafts instantly without friction."
          />

          <FeatureCard
            darkMode={darkMode}
            icon={<FiCalendar />}
            title="Schedule Emails"
            desc="Schedule emails for optimal time with timezone-aware delivery."
          />
        </div>
      </section>

      {/* CTA */}
      <section
        className={`py-28 text-center border-t ${
          darkMode ? "bg-[#090B12] border-gray-800" : "bg-white border-gray-200"
        }`}
      >
        <h2
          className={`text-5xl font-extrabold ${
            darkMode ? "text-white" : "text-gray-900"
          }`}
        >
          Built for modern outreach.
        </h2>

        <p
          className={`mt-8 max-w-3xl mx-auto text-lg leading-8 ${
            darkMode ? "text-gray-400" : "text-gray-600"
          }`}
        >
          A focused AI workspace for founders, marketers and operators who want
          to write better emails faster — without CRM complexity.
        </p>
      </section>

      {/* FOOTER */}
      <footer
        className={`border-t py-10 ${
          darkMode ? "bg-[#090B12] border-gray-800" : "bg-white border-gray-200"
        }`}
      >
        <div className="max-w-7xl mx-auto px-8 flex justify-between text-sm">
          <div
            className={`flex items-center gap-2 font-semibold ${
              darkMode ? "text-white" : "text-gray-900"
            }`}
          >
            <FiMail />
            MailFlow AI
          </div>

          <p className="text-gray-500">© 2026 MailFlow AI</p>
        </div>
      </footer>
    </div>
  );
}

/* FEATURE CARD */
function FeatureCard({ icon, title, desc, darkMode }) {
  return (
    <div
      className={`p-8 rounded-3xl border transition duration-300 hover:-translate-y-2
      ${
        darkMode
          ? "bg-[#11141D] border-gray-800 hover:border-purple-500 hover:shadow-lg hover:shadow-purple-500/10"
          : "bg-white border-gray-200 hover:shadow-xl"
      }`}
    >
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center
        ${
          darkMode
            ? "bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/20"
            : "bg-gray-100"
        }`}
      >
        {icon}
      </div>

      <h3 className="font-bold mt-6">{title}</h3>

      <p
        className={`mt-3 text-sm leading-7 ${
          darkMode ? "text-gray-400" : "text-gray-600"
        }`}
      >
        {desc}
      </p>
    </div>
  );
}
