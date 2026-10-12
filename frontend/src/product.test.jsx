// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import Header from "./components/Header";
import Footer from "./components/Footer";
import SkillPicker from "./components/SkillPicker";
import SavedJobs from "./pages/SavedJobs";
import JobDetails, { safePostingUrl } from "./pages/JobDetails";
import Home from "./pages/Home";
import Clusters from "./pages/Clusters";
import { getJobs, getCompanies, getFacets, getLocations, getJob } from "./api/jobs";
import { getInsights } from "./api/insights";
import { getFavorites } from "./utils/favorites";

vi.mock("./api/jobs", () => ({ getJobs: vi.fn(), getCompanies: vi.fn(), getFacets: vi.fn(), getLocations: vi.fn(), getJob: vi.fn() }));
vi.mock("./api/insights", () => ({ getInsights: vi.fn() }));
vi.mock("chart.js", () => ({ Chart: class { static register() {} destroy() {} }, registerables: [] }));
const job = { sourceKey: "company|job:1", id: "company|job:1", title: "Engineer", company: "Wayve", city: "London", countryCode: "GB", skills: [{ name: "Python", type: "tool" }] };
beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });
afterEach(cleanup);
const show = (page, path = "/") => render(<MemoryRouter initialEntries={[path]}>{page}</MemoryRouter>);

describe("Product navigation and saved jobs", () => {
  it("shows four global destinations with one active Insights entry", () => {
    show(<><Header /><Footer /></>, "/trends");
    const main = screen.getByRole("navigation", { name: "Main navigation" });
    expect(within(main).getAllByRole("link").map(link => link.textContent)).toEqual(["Home", "Jobs", "Insights", "Saved Jobs"]);
    expect(within(main).getByRole("link", { name: "Insights" })).toHaveAttribute("aria-current", "page");
    expect(within(main).queryByRole("link", { name: "Historical trends" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "View Jobs" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Help" })).toHaveLength(1);
  });
  it("renders saved snapshots separately and removes them by source key", async () => {
    localStorage.setItem("av-job-favorites", JSON.stringify([job]));
    show(<SavedJobs />, "/saved");
    expect(screen.getByRole("heading", { name: "Engineer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Engineer" })).toHaveAttribute("href", "/jobs/company%7Cjob%3A1");
    await userEvent.setup().click(screen.getByRole("button", { name: "Remove Engineer from saved jobs" }));
    expect(screen.getByRole("heading", { name: "No saved jobs yet" })).toBeInTheDocument();
    expect(getFavorites()).toEqual([]);
  });
  it("does not crash when saved storage contains a non-array value", () => {
    localStorage.setItem("av-job-favorites", "{}");
    expect(getFavorites()).toEqual([]);
    show(<SavedJobs />);
    expect(screen.getByText("No saved jobs yet")).toBeInTheDocument();
  });
});

describe("Single searchable skill picker", () => {
  it("groups qualifications separately, supports keyboard selection and Escape", async () => {
    const onChange = vi.fn();
    show(<SkillPicker value="" options={[{ value: "Python", count: 7 }, { value: "Bachelor's degree", count: 9 }]} types={{ Python: ["tool"], "Bachelor's degree": ["qualification"] }} onChange={onChange} />);
    const user = userEvent.setup();
    const picker = screen.getByRole("combobox", { name: "Filter by skill" });
    await user.click(picker);
    expect(screen.getByRole("group", { name: "Qualifications" })).toBeInTheDocument();
    await user.type(picker, "Python");
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("Python");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    await user.click(picker); await user.keyboard("{Escape}");
    expect(picker).toHaveAttribute("aria-expanded", "false");
  });
});

describe("Task-first pages", () => {
  it("uses real popular skills and removes misleading skill-total marketing", async () => {
    getJobs.mockResolvedValue({ pagination: { total: 3 } });
    getCompanies.mockResolvedValue([{ name: "Wayve", jobCount: 3 }]);
    getLocations.mockResolvedValue({ locations: [{ countryCode: "GB" }] });
    getFacets.mockResolvedValue({ snapshotDate: "2026-09-25", skill: [{ value: "Python", count: 2 }, { value: "Bachelor's degree", count: 3 }],
      skillTypes: { Python: ["tool"], "Bachelor's degree": ["qualification"] } });
    show(<Home />);
    expect(await screen.findByRole("link", { name: /Python/ })).toHaveAttribute("href", "/jobs?skill=Python");
    expect(screen.queryByText("Skills Tracked")).not.toBeInTheDocument();
    expect(screen.queryByText("Bachelor's degree")).not.toBeInTheDocument();
    expect(screen.getByText("Dataset: 2026-09-25")).toBeInTheDocument();
  });
  it("shows missing facts once, not as repeated empty detail fields", async () => {
    getJob.mockResolvedValue({ data: job });
    show(<JobDetails />);
    await screen.findByRole("heading", { name: "Engineer" });
    expect(screen.getByText("Not stated by the source: salary, work arrangement.")).toBeInTheDocument();
    expect(screen.queryByText("Not specified")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "About Wayve" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Extracted Skills" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Preferred Skills" })).not.toBeInTheDocument();
    expect(safePostingUrl("javascript:alert(1)")).toBe("");
    expect(safePostingUrl("https://example.com/job")).toBe("https://example.com/job");
  });
  it("limits cluster cards, exposes preview skills, and preserves controls in the URL", async () => {
    const groups = Array.from({ length: 25 }, (_, number) => ({ number, name: `Skill group ${number}`, nameStatus: "provisional",
      isNoise: false, jobCount: 30 - number, share: 4, topTerms: [], topSkills: [{ name: "Python", types: ["tool"], jobCount: 1 }], examples: [] }));
    getInsights.mockResolvedValue({ current: { jobCount: 50, clusterCount: 25, companyCount: 1, unclusteredJobs: 0, jobsWithoutSkills: 0, clusters: groups, skills: [] } });
    function Route() { const location = useLocation(); return <output data-testid="route">{location.search}</output>; }
    show(<><Clusters /><Route /></>, "/clusters");
    await screen.findByRole("heading", { name: "Skill group 0" });
    expect(document.querySelectorAll(".cluster-card")).toHaveLength(18);
    expect(document.querySelector(".cluster-card > summary .cluster-preview-skills")).toHaveTextContent("Python");
    await userEvent.setup().click(screen.getByRole("button", { name: "Show more groups" }));
    expect(document.querySelectorAll(".cluster-card")).toHaveLength(25);
    fireEvent.change(screen.getByLabelText("Sort clusters"), { target: { value: "name" } });
    expect(screen.getByTestId("route")).toHaveTextContent("order=name");
    expect(document.querySelectorAll(".cluster-card")).toHaveLength(18);
  });
});
