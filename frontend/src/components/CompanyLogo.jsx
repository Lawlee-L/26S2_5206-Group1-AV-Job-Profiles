import React from "react";

export default function CompanyLogo({
  company,
  large = false,
}) {
  const companyName =
    company?.trim() || "Unknown";

  const shortName = companyName
    .charAt(0)
    .toUpperCase();

  const companyClass = companyName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return (
    <div
      className={`company-logo company-${companyClass} ${
        large ? "large" : ""
      }`}
      title={companyName}
      aria-label={`${companyName} logo`}
    >
      {shortName}
    </div>
  );
}