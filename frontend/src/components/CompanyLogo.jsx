import React, { useState } from "react";

const companyDomains = {
  "Applied Intuition": "appliedintuition.com",
  "WeRide": "weride.ai",
  "Bosch": "bosch.com",
  "Horizon": "horizon.auto",
  "Zoox": "zoox.com",
  "Wayve": "wayve.ai",
  "Mobileye": "mobileye.com",
  "Tensor (AutoX)": "tensor.auto",
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
  "Tier IV": "tier4.co.jp",
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
  "AutoBrains": "autobrains.ai",
  "AImotive": "aimotive.com",
};

const normalise = (name) => name.toLowerCase().replace(/[^a-z0-9]/g, "");
const domains = Object.fromEntries(Object.entries(companyDomains).map(([name, domain]) => [normalise(name), domain]));
domains.avride = "avride.ai";
domains.latitude = "lat.ai";
domains.inceptio = "inceptio.ai";
domains.tensor = "tensor.auto";
domains.tier4 = "tier4.co.jp";

export function logoSources(company, token = "") {
  const domain = domains[normalise(company || "")];
  if (!domain) return [];
  return [
    ...(token.startsWith("pk_") ? [`https://img.logo.dev/${domain}?token=${encodeURIComponent(token)}&size=128&format=png`] : []),
    `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128`,
  ];
}

export default function CompanyLogo({
  company,
  large = false,
}) {
  const companyName = company?.trim() || "Unknown";

  // Key the loader by company: a failed image must not poison the next job card.
  return <LogoImage key={companyName} companyName={companyName} large={large} />;
}

function LogoImage({ companyName, large }) {
  const [sourceIndex, setSourceIndex] = useState(0);
  const [loaded, setLoaded] = useState(false);

  const shortName = companyName
    .charAt(0)
    .toUpperCase();

  const companyClass = companyName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  const sources = logoSources(companyName, import.meta.env.VITE_LOGO_DEV_TOKEN || "");
  const logoUrl = sources[sourceIndex];

  return (
    <div
      className={`company-logo company-${companyClass} ${
        large ? "large" : ""
      }`}
      title={companyName}
      aria-label={logoUrl ? `${companyName} company icon` : `${companyName} initials`}
      aria-busy={Boolean(logoUrl && !loaded)}
    >
      {logoUrl && (
        <img
          src={logoUrl}
          alt={`${companyName} company icon`}
          loading="lazy"
          referrerPolicy="no-referrer"
          onLoad={(event) => { if (event.currentTarget.naturalWidth < 32) { setLoaded(false); setSourceIndex(index => index + 1); } else setLoaded(true); }}
          style={{ opacity: loaded ? 1 : 0 }}
          className="company-logo-image"
          onError={() => { setLoaded(false); setSourceIndex(index => index + 1); }}
        />
      )}
      {(!logoUrl || !loaded) && (
        <span className="company-logo-fallback">
          {shortName}
        </span>
      )}
    </div>
  );
}
