import React from "react";
import {
  Routes,
  Route,
} from "react-router-dom";

import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import JobDetails from "./pages/JobDetails";

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={<Home />}
      />

      <Route
        path="/jobs"
        element={<Jobs />}
      />

      <Route
        path="/jobs/:id"
        element={<JobDetails />}
      />
    </Routes>
  );
}