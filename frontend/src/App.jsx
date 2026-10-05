import React from "react";
import { Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import JobDetails from "./pages/JobDetails";
import About from "./pages/About";

export default function App() {
  return (
    <Routes>
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
    </Routes>
  );
}