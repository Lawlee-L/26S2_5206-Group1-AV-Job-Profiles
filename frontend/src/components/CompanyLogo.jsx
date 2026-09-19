import React from "react";
import { getCompany } from "../data/jobs";

export default function CompanyLogo({ company, large = false }) {
  const c = getCompany(company);
  return (
    <div className={`company-logo ${c.className} ${large ? "large" : ""}`}>
      {c.short}
    </div>
  );
}
