import React, { useState } from "react";

import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";

import { FiTrash2, FiRotateCcw, FiSearch, FiCheck } from "react-icons/fi";

import { useTheme } from "../context/ThemeContext";

const initialDeletedEmails = [
  {
    id: 1,
    recipient: "john@startup.com",
    subject: "Product update announcement",
    deletedAt: "Today, 11:20 AM",
    size: "12 KB",
  },
  {
    id: 2,
    recipient: "marketing@company.com",
    subject: "Monthly newsletter",
    deletedAt: "Yesterday, 4:30 PM",
    size: "18 KB",
  },
  {
    id: 3,
    recipient: "alex@design.io",
    subject: "Design collaboration",
    deletedAt: "Jun 30, 1:15 PM",
    size: "9 KB",
  },
  {
    id: 4,
    recipient: "support@testmail.com",
    subject: "Support request",
    deletedAt: "Jun 25, 9:40 AM",
    size: "7 KB",
  },
];

const DeletedEmails = () => {
  const { darkMode } = useTheme();

  const [deletedEmails, setDeletedEmails] = useState(initialDeletedEmails);

  const [search, setSearch] = useState("");

  const [message, setMessage] = useState("");

  // Restore Email

  const handleRestore = (id) => {
    const restoredEmail = deletedEmails.find((email) => email.id === id);

    setDeletedEmails((prev) => prev.filter((email) => email.id !== id));

    setMessage(`${restoredEmail.subject} restored successfully`);

    setTimeout(() => {
      setMessage("");
    }, 2500);
  };

  // Permanent Delete

  const handlePermanentDelete = (id) => {
    const deletedEmail = deletedEmails.find((email) => email.id === id);

    setDeletedEmails((prev) => prev.filter((email) => email.id !== id));

    setMessage(`${deletedEmail.subject} permanently deleted`);

    setTimeout(() => {
      setMessage("");
    }, 2500);
  };

  const filteredEmails = deletedEmails.filter(
    (email) =>
      email.recipient.toLowerCase().includes(search.toLowerCase()) ||
      email.subject.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div
      className={`flex h-screen transition-all duration-500 ${
        darkMode
          ? "bg-[#090B12] text-white"
          : "bg-gradient-to-br from-gray-50 via-white to-gray-100 text-gray-900"
      }`}
    >
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Navbar />

        <div className="p-8 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {/* MESSAGE */}

            {message && (
              <div
                className={`mb-5 flex items-center gap-2 px-5 py-3 rounded-xl w-fit ${
                  darkMode
                    ? "bg-green-500/20 text-green-300"
                    : "bg-green-100 text-green-700"
                }`}
              >
                <FiCheck />
                {message}
              </div>
            )}

            {/* HEADER */}

            <div className="flex justify-between items-start mb-8">
              <div className="flex items-center gap-3">
                <div
                  className={`p-3 rounded-xl ${
                    darkMode
                      ? "bg-red-500/20 text-red-300"
                      : "bg-red-100 text-red-600"
                  }`}
                >
                  <FiTrash2 size={24} />
                </div>

                <div>
                  <h1 className="text-3xl font-bold">Deleted Emails</h1>

                  <p className="text-sm text-gray-500 mt-1">
                    Manage emails moved to trash.
                  </p>
                </div>
              </div>

              <div
                className={`px-5 py-3 rounded-xl border ${
                  darkMode
                    ? "bg-[#11141D] border-gray-800"
                    : "bg-white border-gray-200"
                }`}
              >
                <p className="text-sm text-gray-500">Trash Items</p>

                <h2 className="text-2xl font-bold">{deletedEmails.length}</h2>
              </div>
            </div>

            {/* SEARCH */}

            <div className="mb-6">
              <div
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border max-w-md ${
                  darkMode
                    ? "bg-[#11141D] border-gray-800"
                    : "bg-white border-gray-200"
                }`}
              >
                <FiSearch className="text-gray-400" />

                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search deleted emails..."
                  className={`bg-transparent outline-none w-full text-sm ${
                    darkMode
                      ? "text-white placeholder-gray-500"
                      : "text-gray-800"
                  }`}
                />
              </div>
            </div>

            {/* TABLE */}

            <div
              className={`rounded-2xl border overflow-hidden shadow-xl ${
                darkMode
                  ? "bg-[#11141D] border-gray-800"
                  : "bg-white border-gray-200"
              }`}
            >
              <div
                className={`grid grid-cols-5 px-6 py-4 border-b text-xs font-semibold uppercase text-gray-500 ${
                  darkMode ? "bg-[#151923] border-gray-800" : "bg-gray-50"
                }`}
              >
                <div>Recipient</div>
                <div>Subject</div>
                <div>Deleted At</div>
                <div>Size</div>
                <div>Actions</div>
              </div>

              {filteredEmails.length > 0 ? (
                filteredEmails.map((email) => (
                  <div
                    key={email.id}
                    className={`grid grid-cols-5 px-6 py-5 items-center border-b transition ${
                      darkMode
                        ? "border-gray-800 hover:bg-[#151923]"
                        : "border-gray-100 hover:bg-gray-50"
                    }`}
                  >
                    <div className="font-medium">{email.recipient}</div>

                    <div className="text-gray-500">{email.subject}</div>

                    <div className="text-gray-500 text-sm">
                      {email.deletedAt}
                    </div>

                    <div className="text-gray-500">{email.size}</div>

                    <div className="flex gap-3">
                      <button
                        onClick={() => handleRestore(email.id)}
                        className={`p-2 rounded-lg ${
                          darkMode
                            ? "bg-blue-500/20 text-blue-300"
                            : "bg-blue-50 text-blue-600"
                        }`}
                        title="Restore"
                      >
                        <FiRotateCcw size={17} />
                      </button>

                      <button
                        onClick={() => handlePermanentDelete(email.id)}
                        className={`p-2 rounded-lg ${
                          darkMode
                            ? "bg-red-500/20 text-red-300"
                            : "bg-red-50 text-red-600"
                        }`}
                        title="Delete permanently"
                      >
                        <FiTrash2 size={17} />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-10 text-center text-gray-500">
                  No deleted emails found
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeletedEmails;
