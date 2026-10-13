// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Clusters from "./pages/Clusters";
import Trends from "./pages/Trends";
import CompanyLogo, { logoSources } from "./components/CompanyLogo";
import { chartConfig } from "./components/InsightChart";
import { getInsights } from "./api/insights";

vi.mock("./api/insights", () => ({ getInsights: vi.fn() }));
vi.mock("chart.js", () => ({ Chart: class { static register() {} destroy() {} }, registerables: [] }));
const current = { releaseKey: "release-1", jobCount: 3, clusterCount: 1, unclusteredJobs: 1, companyCount: 1, jobsWithoutSkills: 0,
  skills: [{ name: "Python", types: ["tool"], jobCount: 2 }],
  clusters: [{ number: 25, name: "Motion planning & control", nameStatus: "provisional", isNoise: false, jobCount: 2, share: 66.67,
    topTerms: ["planning"], topSkills: [{ name: "Python", jobCount: 2 }], companies: [], examples: [{ title: "Planner", sourceKey: "a|b|1", company: "Wayve" }] },
    { number: -1, name: "Unclustered AV roles", nameStatus: "unclustered", isNoise: true, jobCount: 1, share: 33.33,
      topTerms: [], topSkills: [], companies: [], examples: [] }] };
const point = { date: "2026-09-25", activeJobs: 6, avJobs: 3, companyCount: 1, sourceCount: 1, clusterCount: 1, unclusteredShare: 33.33,
  classificationStatus: "ready", collectionStatus: "partial", runKind: "cumulative_state_export", timeQuality: "date_only", sourceReportAvailable: false };
const history = { classifiedVersionCount: 1, points: [point], skillSeries: [{ name: "Python", values: [{ share: 66.67, jobCount: 2 }] }] };
beforeEach(() => getInsights.mockResolvedValue({ current, history }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const show = (page) => render(<MemoryRouter>{page}</MemoryRouter>);

describe("Analysis pages", () => {
  it("shows provisional groups, skill search, and real example job links", async () => {
    show(<Clusters />);
    await screen.findByText("Provisional");
    expect(screen.getByRole("link", { name: "Planner" })).toHaveAttribute("href", "/jobs/a%7Cb%7C1");
    fireEvent.change(screen.getByLabelText("Search clusters and skills"), { target: { value: "python" } });
    expect(screen.getByRole("heading", { name: "Motion planning & control" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Unclustered AV roles" })).not.toBeInTheDocument();
  });
  it("distinguishes unclustered AV jobs from irrelevant jobs", async () => {
    show(<Clusters />);
    await screen.findByText("Provisional");
    fireEvent.change(screen.getByLabelText("Cluster grouping"), { target: { value: "unclustered" } });
    expect(screen.getByRole("heading", { name: "Unclustered AV roles" })).toBeInTheDocument();
    expect(screen.queryByText("Provisional")).not.toBeInTheDocument();
  });
  it("shows an honest empty state and pending analysis when only one version is classified", async () => {
    getInsights.mockResolvedValue({ current, history: { ...history, points: [{ ...point, date: "2026-09-06", avJobs: null, clusterCount: null, unclusteredShare: null }, point],
      skillSeries: [{ name: "Python", values: [{ share: null, jobCount: null }, { share: 66.67, jobCount: 2 }] }] } });
    show(<Trends />);
    expect(await screen.findByText(/Only 1 classified snapshot/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Data coverage & sources/));
    expect(screen.getByText("Pending published analysis")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
    expect(screen.queryByRole("img", { name: /Skill demand across snapshots/ })).not.toBeInTheDocument();
  });
  it("shows real series for two classified dates and restricts the selected period", async () => {
    const old = { ...point, date: "2026-09-06" };
    getInsights.mockResolvedValue({ current, history: { ...history, classifiedVersionCount: 2, points: [old, point],
      skillSeries: [{ name: "Python", values: [{ date: old.date, share: 50, jobCount: 1 }, { date: point.date, share: 66.67, jobCount: 2 }] }] } });
    show(<Trends />);
    await screen.findByRole("img", { name: /Skill demand across snapshots/ });
    expect(screen.getByRole("img", { name: /Skill demand across snapshots/ })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Skill trend measure"), { target: { value: "jobCount" } });
    expect(screen.getByText("Distinct active AV jobs requiring each skill.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Python" }));
    expect(screen.getByText("Select a skill to display its history.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Trend start date"), { target: { value: point.date } });
    expect(screen.getByRole("heading", { name: "Not enough history to show changes" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /Skill demand across snapshots/ })).not.toBeInTheDocument();
  });
  it("handles an unavailable backend and supports retry", async () => {
    getInsights.mockRejectedValueOnce(new Error("Backend unavailable"));
    show(<Clusters />);
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("Provisional");
  });
  it("draws null gaps, not fake continuous histories", () => {
    const config = chartConfig({ type: "line", labels: ["a", "b", "c"], series: [{ name: "Skill", values: [10, null, 20] }], percent: true });
    expect(config.data.datasets[0].spanGaps).toBe(false);
    expect(config.data.datasets[0].data).toEqual([10, null, 20]);
    expect(config.options.scales.y.max).toBe(100);
  });
});

describe("Company icons", () => {
  it("works without a personal key, normalises aliases, and ignores secret keys", () => {
    expect(logoSources("xPeNg")[0]).toContain("xpeng.com");
    expect(logoSources("AV Ride")[0]).toContain("avride.ai");
    expect(logoSources("Tier IV")[0]).toContain("tier4.co.jp");
    expect(logoSources("Wayve", "sk_private")).toHaveLength(1);
    expect(logoSources("Wayve", "pk_public")).toHaveLength(2);
    expect(logoSources("Unknown")).toEqual([]);
  });
  it("falls back safely and resets failure when the company changes", async () => {
    const { rerender } = render(<CompanyLogo company="Wayve" />);
    fireEvent.error(screen.getByRole("img", { name: "Wayve company icon" }));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("W")).toBeInTheDocument();
    rerender(<CompanyLogo company="Kodiak" />);
    expect(screen.getByRole("img", { name: "Kodiak company icon" })).toBeInTheDocument();
  });
  it("keeps initials during loading and rejects tiny placeholder icons", () => {
    render(<CompanyLogo company="Wayve" />);
    expect(screen.getByText("W")).toBeInTheDocument();
    const icon = screen.getByRole("img", { name: "Wayve company icon" });
    Object.defineProperty(icon, "naturalWidth", { value: 16 });
    fireEvent.load(icon);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("W")).toBeInTheDocument();
  });
});
