import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";

import { FiSave, FiArrowLeft, FiCheckCircle } from "react-icons/fi";

import { useTheme } from "../context/ThemeContext";

export default function EditEmail() {
  const { darkMode } = useTheme();

  const navigate = useNavigate();

  const [draftId, setDraftId] = useState(null);

  const [notification, setNotification] = useState("");

  const [formData, setFormData] = useState({
    purpose: "",
    tone: "",
    length: "",
    sender: "",
    recipient: "",
    email: "",
    company: "",
    context: "",
  });

  const [generatedEmail, setGeneratedEmail] = useState("");

  // LOAD SELECTED DRAFT

  useEffect(() => {
    const savedDraft = JSON.parse(localStorage.getItem("selectedDraft"));

    if (savedDraft) {
      setDraftId(savedDraft.id);

      setFormData(savedDraft.formData);

      setGeneratedEmail(savedDraft.generatedEmail || "");
    }
  }, []);

  const handleChange = (name, value) => {
    setFormData((prev) => ({
      ...prev,

      [name]: value,
    }));
  };

  // UPDATE DRAFT

  const updateDraft = () => {
    const drafts = JSON.parse(localStorage.getItem("drafts")) || [];

    const updatedDrafts = drafts.map((draft) => {
      if (draft.id === draftId) {
        return {
          ...draft,

          formData,

          generatedEmail,

          updatedAt: new Date().toLocaleString(),
        };
      }

      return draft;
    });

    localStorage.setItem("drafts", JSON.stringify(updatedDrafts));

    setNotification("Draft updated successfully");

    setTimeout(() => {
      setNotification("");

      navigate("/drafts");
    }, 1500);
  };

  return (
    <div
      className={`flex h-screen ${
        darkMode
          ? "bg-[#090B12] text-white"
          : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"
      }`}
    >
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Navbar />

        <main className="p-8 overflow-y-auto">
          {notification && (
            <div
              className={`mb-5 px-5 py-3 rounded-xl flex items-center gap-2 w-fit ${
                darkMode
                  ? "bg-green-500/20 text-green-300"
                  : "bg-green-100 text-green-700"
              }`}
            >
              <FiCheckCircle />

              {notification}
            </div>
          )}

          <div
            className={`rounded-3xl p-8 border shadow-xl ${
              darkMode
                ? "bg-[#11141D] border-gray-800"
                : "bg-white border-gray-200"
            }`}
          >
            <div className="flex justify-between items-center mb-8">
              <div>
                <h1 className="text-3xl font-bold">Edit Email Draft</h1>

                <p className="text-gray-500 mt-2">Update your saved email</p>
              </div>

              <button
                onClick={() => navigate("/drafts")}
                className="flex items-center gap-2 text-gray-500"
              >
                <FiArrowLeft />
                Back
              </button>
            </div>

            {/* INPUTS */}

            <div className="grid md:grid-cols-2 gap-5">
              <input
                value={formData.recipient}
                onChange={(e) => handleChange("recipient", e.target.value)}
                placeholder="Recipient Name"
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              />

              <input
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="Email"
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              />

              <input
                value={formData.company}
                onChange={(e) => handleChange("company", e.target.value)}
                placeholder="Company"
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              />

              <input
                value={formData.sender}
                onChange={(e) => handleChange("sender", e.target.value)}
                placeholder="Sender Name"
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              />
            </div>

            <div className="grid md:grid-cols-3 gap-5 mt-5">
              <select
                value={formData.purpose}
                onChange={(e) => handleChange("purpose", e.target.value)}
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              >
                <option>Cold Outreach</option>
                <option>Follow-Up</option>
                <option>Networking</option>
                <option>Job Application</option>
                <option>Partnership</option>
                <option>Thank You</option>
              </select>

              <select
                value={formData.tone}
                onChange={(e) => handleChange("tone", e.target.value)}
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              >
                <option>Professional</option>
                <option>Persuasive</option>
                <option>Friendly</option>
                <option>Casual</option>
                <option>Formal</option>
              </select>

              <select
                value={formData.length}
                onChange={(e) => handleChange("length", e.target.value)}
                className={`p-3 rounded-xl border ${
                  darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
                }`}
              >
                <option>Short</option>
                <option>Medium</option>
                <option>Long</option>
              </select>
            </div>

            <textarea
              rows="5"
              value={generatedEmail}
              onChange={(e) => setGeneratedEmail(e.target.value)}
              className={`w-full mt-6 p-4 rounded-xl border ${
                darkMode ? "bg-[#090B12] border-gray-700" : "border-gray-200"
              }`}
            />

            <button
              onClick={updateDraft}
              className={`mt-6 px-6 py-3 rounded-xl text-white flex items-center gap-2 ${
                darkMode
                  ? "bg-gradient-to-r from-indigo-500 to-purple-600"
                  : "bg-gray-900"
              }`}
            >
              <FiSave />
              Update Draft
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}
