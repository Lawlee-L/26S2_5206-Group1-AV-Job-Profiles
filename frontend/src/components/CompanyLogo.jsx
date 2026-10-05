import React, { useState } from "react";

const companyDomains = {
  "Applied Intuition": "appliedintuition.com",
  "WeRide": "weride.ai",
  "Bosch": "bosch.com",
  "Horizon": "horizon.auto",
  "Zoox": "zoox.com",
  "Wayve": "wayve.ai",
  "Mobileye": "mobileye.com",
  "Tensor (AutoX)": "autox.ai",
  "Woven": "woven.toyota",
  "42dot": "42dot.ai",
  "Inceptio.ai": "inceptio.ai",
  "Waabi": "waabi.ai",
  "DeepRoute": "deeproute.ai",
  "Nuro": "nuro.ai",
  "Motional": "motional.com",
  "Aurora": "aurora.tech",
  "Kodiak": "kodiak.ai",
  "Gatik": "gatik.ai",
  "Tier IV": "tier4.jp",
  "Torc AI": "torc.ai",
  "May Mobility": "maymobility.com",
  "GM": "gm.com",
  "Plus AI": "plus.ai",
  "Latitude (Ford)": "lat.ai",
  "Avride": "avride.ai",
  "Bot.Auto": "bot.auto",
  "Einride": "einride.tech",
  "XPeng": "xpeng.com",
  "Pony.AI": "pony.ai",
  "Vay": "vay.io",
  "Stack AV": "stackav.com",
  "AutoBrains": "autobrains.com",
  "AImotive": "aimotive.com",
};

export default function CompanyLogo({
  company,
  large = false,
}) {
  const companyName = company?.trim() || "Unknown";

  const [imageError, setImageError] = useState(false);

  const shortName = companyName
    .charAt(0)
    .toUpperCase();

  const companyClass = companyName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  const domain = companyDomains[companyName];

  const token =
    import.meta.env.VITE_LOGO_DEV_TOKEN;

  const logoUrl =
    domain && token
      ? `https://img.logo.dev/${domain}?token=${token}&size=128&format=png`
      : null;

  return (
    <div
      className={`company-logo company-${companyClass} ${
        large ? "large" : ""
      }`}
      title={companyName}
      aria-label={`${companyName} logo`}
    >
      {logoUrl && !imageError ? (
        <img
          src={logoUrl}
          alt={`${companyName} logo`}
          className="company-logo-image"
          onError={() => setImageError(true)}
        />
      ) : (
        <span className="company-logo-fallback">
          {shortName}
        </span>
      )}
    </div>
  );
}