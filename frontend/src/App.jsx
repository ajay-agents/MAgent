import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Homepage        from "./pages/Homepage.jsx";
import Dashboard       from "./pages/Dashboard.jsx";
import CreateEmail     from "./pages/CreateEmail.jsx";
import ScheduledEmails from "./pages/ScheduledEmails.jsx";
import SentEmails      from "./pages/SentEmails.jsx";
import DeletedEmails   from "./pages/DeletedEmails.jsx";
import Drafts          from "./pages/Drafts.jsx";
import EditEmail       from "./pages/EditEmail.jsx";
import Settings        from "./pages/Settings.jsx";
import AuthModal       from "./pages/AuthModal";
import ProtectedRoute  from "./components/ProtectedRoute";

const App = () => {
  const [open, setOpen] = useState(false);

  return (
    <BrowserRouter>
      <AuthModal isOpen={open} onClose={() => setOpen(false)} />

      <Routes>
        <Route path="/" element={<Homepage setAuthOpen={setOpen} />} />

        <Route path="/dashboard"       element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/create-email"    element={<ProtectedRoute><CreateEmail /></ProtectedRoute>} />
        <Route path="/scheduled-emails" element={<ProtectedRoute><ScheduledEmails /></ProtectedRoute>} />
        <Route path="/sent-emails"     element={<ProtectedRoute><SentEmails /></ProtectedRoute>} />
        <Route path="/deleted-emails"  element={<ProtectedRoute><DeletedEmails /></ProtectedRoute>} />
        <Route path="/drafts"          element={<ProtectedRoute><Drafts /></ProtectedRoute>} />
        <Route path="/settings"        element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/edit-email"      element={<ProtectedRoute><EditEmail /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
