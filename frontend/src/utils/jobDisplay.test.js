import { describe, it, expect } from "vitest";
import { compactText, locationText, salaryText, workArrangement, groupedSkills } from "./jobDisplay";

describe("job presentation", () => {
  it("deduplicates case variants across skill types and separates qualifications", () => {
    const groups = groupedSkills([{ name: "Python", type: "tool" }, { name: "python", type: "domain" },
      { name: "Bachelor's degree", type: "qualification" }, null]);
    expect(groups["Tools & technical skills"]).toEqual(["Python"]);
    expect(groups["Domain knowledge"]).toEqual([]);
    expect(groups.Qualifications).toEqual(["Bachelor's degree"]);
  });
  it("retains a complete range and monthly currency information", () => {
    expect(salaryText({ salaryMin: 0, salaryMax: 500, salaryCurrency: "JPY", salaryPeriod: "month" }))
      .toBe("JPY 0–500 per month");
    expect(salaryText({ salaryMax: 500 })).toBe("Up to Currency not stated 500 (period not stated)");
    expect(salaryText({ salaryMin: 500 })).toBe("From Currency not stated 500 (period not stated)");
    expect(salaryText({ salary: "想定月収 / Estimated Monthly Salary: 483,334円 ~ 1,375,000円",
      salaryMin: 483334, salaryMax: 1375000, salaryCurrency: "JPY", salaryPeriod: "month" }))
      .toBe("JPY 483,334–1,375,000 per month");
    expect(salaryText({ salaryMin: 75000, salaryMax: 300000, salaryCurrency: "USD",
      salaryNormalization: { qualifier: "San Jose, California, US" } }))
      .toContain("applies to San Jose, California, US");
  });
  it("does not invent pay or work arrangements", () => {
    expect(salaryText({})).toBe("Salary not available");
    expect(workArrangement({ employmentType: "full-time" })).toBe("Not specified");
    expect(workArrangement({ remoteType: "hybrid" })).toBe("Hybrid");
  });
  it("uses known hierarchy or source location without guessing", () => {
    expect(locationText({ city: "Berlin", stateRegion: "Berlin", countryCode: "DE" })).toBe("Berlin, Germany");
    expect(locationText({ locationDisplay: "US | Germany" })).toBe("US | Germany");
    expect(locationText({})).toBe("Location not specified");
  });
  it("compacts previews without modifying the original value", () => {
    const original = "Monthly salary\nOvertime allowance";
    expect(compactText(original)).toBe("Monthly salary");
    expect(original).toBe("Monthly salary\nOvertime allowance");
    expect(compactText("abcdef", 5)).toBe("abcd…");
  });
});
