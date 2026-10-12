import React, { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import JobDetails from "./pages/JobDetails";
import About from "./pages/About";
import Help from "./pages/Help";
import Terms from "./pages/Terms";
import SavedJobs from "./pages/SavedJobs";
const Clusters = lazy(() => import("./pages/Clusters"));
const Trends = lazy(() => import("./pages/Trends"));

export default function App() {
  return (
    <Suspense fallback={<div className="container py-5" role="status">Loading page…</div>}><Routes>
      <Route path="/clusters" element={<Clusters />} />
      <Route path="/trends" element={<Trends />} />
      <Route path="/saved" element={<SavedJobs />} />
      {/* HOME */}
      <Route
        path="/"
        element={<Home />}
      />

      {/* JOBS */}
      <Route
        path="/jobs"
        element={<Jobs />}
      />

      {/* JOB DETAILS */}
      <Route
        path="/jobs/:id"
        element={<JobDetails />}
      />

      {/* ABOUT + FAVORITES */}
      <Route
        path="/about"
        element={<About />}
      />

      {/* HELP */}
      <Route
        path="/help"
        element={<Help />}
      />

      {/* TERMS AND CONDITIONS */}
      <Route
        path="/terms"
        element={<Terms />}
      />
    </Routes></Suspense>
  );
}
