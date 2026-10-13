// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import React from "react";
import { beforeEach, afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, cleanup, within, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import App from "./App";
import { getJobs } from "./api/jobs";
import { useJobFilters } from "./hooks/useJobFilters";

const geo = [
  { countryCode: "US", stateRegion: "CA", city: "San Francisco", jobCount: 1 },
  { countryCode: "DE", stateRegion: "Berlin", city: "Berlin", jobCount: 1 },
];
const job = { sourceKey: "greenhouse|kodiak|id:42", company: "Kodiak", title: "AV Engineer",
  location: "<p>Long original address</p>", locationDisplay: "Long original address\nMore locations",
  countryCode: "US", stateRegion: "CA", city: "San Francisco", remoteType: "hybrid",
  salary: "<p>USD 100,000</p>", salaryDisplay: "USD 100,000\nAdditional benefits", skills: [],
  postedDate: "2026-09-25", description: "<p>Engineering</p>", descriptionDisplay: "Engineering" };

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (input) => {
    const url = new URL(input, "http://localhost");
    let body;
    if (url.pathname === "/api/job-facets") body = { data: facetFixture() };
    else if (url.pathname === "/api/locations") body = { data: { locations: geo } };
    else if (url.pathname === "/api/salary-options") body = { data: { options: [
      { currency: "USD", period: "year", jobCount: 1 }, { currency: "JPY", period: "month", jobCount: 1 },
    ] } };
    else if (url.pathname === "/api/companies") body = { data: [{ name: "Kodiak", jobCount: 1 }] };
    else if (url.pathname === "/api/skills") body = { data: [{ name: "C++" }, { name: "Python" }] };
    else if (url.pathname === "/api/jobs") {
      const country = url.searchParams.get("country");
      if (country && !/^[A-Z]{2}$/.test(country)) return { ok: false, status: 400, json: async () => ({ error: "country must be a two-letter country code" }) };
      body = { data: [job], pagination: { total: 1, totalPages: 1, page: 1 } };
    } else body = { data: job };
    return { ok: true, json: async () => body };
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function RouteProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  return <><output data-testid="route">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(-1)}>Browser back</button></>;
}
const mount = (path = "/jobs") => render(<MemoryRouter initialEntries={[path]}><App /><RouteProbe /></MemoryRouter>);
const lastJobUrl = () => new URL(fetch.mock.calls.filter(([url]) => new URL(url, "http://localhost").pathname === "/api/jobs").at(-1)[0], "http://localhost");
function facetFixture() {
  return { company: [{ value: "Kodiak", count: 1 }], country: [{ value: "US", count: 1 }, { value: "DE", count: 1 }],
    state_region: [{ value: "CA", count: 1 }, { value: "Berlin", count: 1 }],
    city: [{ value: "San Francisco", count: 1 }, { value: "Berlin", count: 1 }],
    remote_type: [{ value: "hybrid", count: 1 }], seniority: [{ value: "mid", count: 1 }],
    skill: [{ value: "C++", count: 1 }, { value: "Python", count: 1 }],
    has_salary: [{ value: "true", count: 1 }, { value: "false", count: 1 }],
    salary_units: [{ value: "USD/year", count: 1 }, { value: "JPY/month", count: 1 }] };
}
async function select(user, label, value) {
  const control = screen.getByLabelText(label);
  await waitFor(() => expect(control).not.toBeDisabled());
  if (label === "Filter by skill") {
    await user.click(control);
    await user.type(control, value);
    await user.click(await screen.findByRole("option", { name: name => name.startsWith(value + " (") }));
  } else await user.selectOptions(control, value);
}
async function advanced(user) {
  await user.click(screen.getByRole("button", { name: "More filters" }));
}

describe("real frontend API serialization", () => {
  it("uses the same-origin API proxy by default", async () => {
    await getJobs();
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/jobs\?/), expect.anything());
  });

  it("applies salary bounds with explicit units and clears stale bounds on unit change", async () => {
    const user = userEvent.setup(); mount();
    await advanced(user);
    await screen.findByRole("option", { name: "USD / year (1)" });
    expect(screen.getByLabelText("Minimum salary")).toBeDisabled();
    await select(user, "Salary currency and period", "USD/year");
    await user.type(screen.getByLabelText("Minimum salary"), "100000");
    await user.type(screen.getByLabelText("Maximum salary"), "200000");
    await user.click(screen.getByRole("button", { name: "Apply salary range" }));
    await waitFor(() => expect(lastJobUrl().searchParams.get("salary_min")).toBe("100000"));
    expect(lastJobUrl().searchParams.get("salary_currency")).toBe("USD");
    expect(lastJobUrl().searchParams.get("salary_period")).toBe("year");
    await select(user, "Salary currency and period", "JPY/month");
    await waitFor(() => expect(lastJobUrl().searchParams.get("salary_currency")).toBe("JPY"));
    expect(lastJobUrl().searchParams.has("salary_min")).toBe(false);
    expect(screen.getByLabelText("Minimum salary")).toHaveValue(null);
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(lastJobUrl().searchParams.has("salary_currency")).toBe(false));
  });

  it("does not send reversed salary bounds", async () => {
    const user = userEvent.setup(); mount();
    await advanced(user);
    await screen.findByRole("option", { name: "USD / year (1)" });
    await select(user, "Salary currency and period", "USD/year");
    await user.type(screen.getByLabelText("Minimum salary"), "200");
    await user.type(screen.getByLabelText("Maximum salary"), "100");
    await user.click(screen.getByRole("button", { name: "Apply salary range" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Minimum must not exceed maximum");
    expect(lastJobUrl().searchParams.has("salary_min")).toBe(false);
  });
  it("uses country codes and resets dependent location filters", async () => {
    const user = userEvent.setup(); mount();
    await advanced(user);
    await screen.findByRole("option", { name: "United States (1)" });
    const country = screen.getByLabelText("Filter by country");
    await select(user, "Filter by country", "US");
    await select(user, "Filter by state or region", "CA");
    await select(user, "Filter by city", "San Francisco");
    await waitFor(() => expect(lastJobUrl().searchParams.get("city")).toBe("San Francisco"));
    expect(lastJobUrl().searchParams.get("country")).toBe("US");
    await select(user, "Filter by country", "DE");
    await waitFor(() => expect(lastJobUrl().searchParams.get("country")).toBe("DE"));
    expect(lastJobUrl().searchParams.has("state_region")).toBe(false);
    expect(lastJobUrl().searchParams.has("city")).toBe(false);
    expect(screen.getByLabelText("Filter by city")).toHaveValue("");
  });

  it("combines new filters, URL-encodes skills, and clears them", async () => {
    const user = userEvent.setup(); mount();
    await advanced(user);
    await waitFor(() => expect(screen.getByLabelText("Filter by skill")).not.toBeDisabled());
    await select(user, "Filter by skill", "C++");
    await select(user, "Filter by salary information", "false");
    fireEvent.change(screen.getByLabelText("Posted since"), { target: { value: "2026-09-01" } });
    await user.selectOptions(screen.getByLabelText("Sort jobs"), "title");
    await waitFor(() => expect(lastJobUrl().searchParams.get("sort")).toBe("title"));
    expect(lastJobUrl().searchParams.get("skill")).toBe("C++");
    expect(lastJobUrl().searchParams.get("has_salary")).toBe("false");
    expect(lastJobUrl().searchParams.get("posted_after")).toBe("2026-09-01");
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(lastJobUrl().searchParams.has("skill")).toBe(false));
    expect(lastJobUrl().searchParams.has("has_salary")).toBe(false);
    expect(lastJobUrl().searchParams.has("posted_after")).toBe(false);
    expect(lastJobUrl().searchParams.get("sort")).toBe("newest");
  });

  it("keeps structured location and salary separate on cards", async () => {
    mount();
    const heading = await screen.findByRole("heading", { name: "AV Engineer" });
    const card = heading.closest("article");
    expect(within(card).getByText("San Francisco, CA, United States")).toBeInTheDocument();
    expect(within(card).getByText(/USD 100,000/).closest("p")).toHaveClass("job-salary-text");
    expect(card).not.toHaveTextContent("<p>");
  });

  it("shows separate expandable full source fields in detail", async () => {
    mount(`/jobs/${encodeURIComponent(job.sourceKey)}`);
    await screen.findByRole("heading", { name: "AV Engineer" });
    expect(screen.getByText("Full location information from the source").closest("details")).toHaveTextContent("More locations");
    expect(screen.getByText("Full salary information from the source").closest("details")).toHaveTextContent("Additional benefits");
    expect(screen.queryByText("Employment Type")).not.toBeInTheDocument();
    expect(screen.getAllByText("Work Arrangement")).toHaveLength(1);
  });

  it("preserves backend validation error messages", async () => {
    fetch.mockResolvedValue({ ok: false, status: 400, json: async () => ({ error: "posted_after must be a date in YYYY-MM-DD format" }) });
    await expect(getJobs({ postedAfter: "invalid" })).rejects.toThrow("posted_after must be a date");
  });

  it("finds a rare skill without rendering thousands of options", async () => {
    const original = fetch.getMockImplementation();
    fetch.mockImplementation(async (input) => {
      if (new URL(input, "http://localhost").pathname === "/api/job-facets") return { ok: true, json: async () => ({
        data: { ...facetFixture(), skill: [...Array.from({ length: 200 }, (_, i) => ({ value: `Common ${i}`, count: 1 })), { value: "Z-rare skill", count: 1 }] },
      }) };
      return original(input);
    });
    const user = userEvent.setup(); mount();
    await waitFor(() => expect(screen.getByLabelText("Filter by skill")).not.toBeDisabled());
    await user.click(screen.getByLabelText("Filter by skill"));
    await screen.findByRole("option", { name: "Common 0 (1)" });
    expect(within(screen.getByRole("listbox", { name: "Available skills" })).getAllByRole("option")).toHaveLength(60);
    await user.type(screen.getByLabelText("Filter by skill"), "Z-rare");
    await user.click(await screen.findByRole("option", { name: "Z-rare skill (1)" }));
    await waitFor(() => expect(lastJobUrl().searchParams.get("skill")).toBe("Z-rare skill"));
  });

  it("narrows country and work options after company selection", async () => {
    const original = fetch.getMockImplementation();
    fetch.mockImplementation(async input => {
      const url = new URL(input, "http://localhost");
      if (url.pathname === "/api/job-facets" && url.searchParams.get("company") === "Kodiak") {
        return { ok: true, json: async () => ({ data: { ...facetFixture(), country: [{ value: "US", count: 1 }] } }) };
      }
      return original(input);
    });
    const user = userEvent.setup(); mount();
    await screen.findByRole("option", { name: "Germany (1)" });
    await select(user, "Filter by company", "Kodiak");
    await waitFor(() => expect(screen.queryByRole("option", { name: "Germany (1)" })).not.toBeInTheDocument());
    await select(user, "Filter by country", "US");
    await waitFor(() => expect(lastJobUrl().searchParams.get("country")).toBe("US"));
    expect(lastJobUrl().searchParams.get("company")).toBe("Kodiak");
    await user.click(screen.getByRole("button", { name: "Remove Company filter" }));
    await screen.findByRole("option", { name: "Germany (1)" });
  });

  for (const back of ["Back to Jobs", "Browser back"]) {
    it(`restores every filter and pagination through ${back}`, async () => {
      const path = "/jobs?company=Kodiak&country=US&state_region=CA&city=San+Francisco&remote_type=hybrid&seniority=mid&skill=C%2B%2B&posted_after=2026-09-01&has_salary=true&salary_currency=USD&salary_period=year&salary_min=100&salary_max=200&sort=title&page=2";
      const user = userEvent.setup(); mount(path);
      const title = await screen.findByRole("heading", { name: "AV Engineer" });
      await user.click(within(title).getByRole("link"));
      await screen.findByRole("heading", { name: "AV Engineer" });
      await user.click(screen.getByRole(back === "Browser back" ? "button" : "link", { name: back }));
      await screen.findByRole("heading", { name: "Find your next opportunity." });
      expect(screen.getByTestId("route")).toHaveTextContent(path);
      expect(screen.getByLabelText("Filter by company")).toHaveValue("Kodiak");
      expect(screen.getByLabelText("Filter by city")).toHaveValue("San Francisco");
      expect(screen.getByLabelText("Filter by skill")).toHaveValue("C++");
      expect(screen.getByLabelText("Minimum salary")).toHaveValue(100);
      await waitFor(() => expect(lastJobUrl().searchParams.get("page")).toBe("2"));
      expect(lastJobUrl().searchParams.get("sort")).toBe("title");
    });
  }

  it("keeps active advanced filters when collapsed and leaves skill selection visible", async () => {
    const user = userEvent.setup(); mount("/jobs?skill=Python&has_salary=true");
    await waitFor(() => expect(screen.getByLabelText("Filter by skill")).not.toBeDisabled());
    await user.click(screen.getByRole("button", { name: /Hide additional filters/ }));
    expect(screen.getByLabelText("Filter by salary information").closest("#advanced-filters")).toHaveAttribute("hidden");
    expect(screen.getByLabelText("Filter by skill")).toBeVisible();
    expect(screen.getByTestId("route")).toHaveTextContent("skill=Python");
    await user.click(screen.getByRole("button", { name: /More filters/ }));
    expect(screen.getByLabelText("Filter by skill")).toHaveValue("Python");
  });

  it("does not offer stale global options when facets fail, and supports retry", async () => {
    const original = fetch.getMockImplementation();
    let failed = true;
    fetch.mockImplementation(async input => new URL(input, "http://localhost").pathname === "/api/job-facets" && failed
      ? { ok: false, status: 503, json: async () => ({ error: "Options temporarily unavailable" }) } : original(input));
    const user = userEvent.setup(); mount("/jobs?company=Kodiak");
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Filter by country")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Clear" })).not.toBeDisabled();
    failed = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByLabelText("Filter by country")).not.toBeDisabled());
  });

  it("links to the actual project repository, with no placeholder contact", async () => {
    mount();
    expect(screen.getByRole("link", { name: "Project on GitHub" })).toHaveAttribute("href",
      "https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles");
    expect(document.querySelector('a[href^="mailto:"]')).toBeNull();
  });

  it("does not lose successive URL edits made before React rerenders", async () => {
    function FastEdits() {
      const { update } = useJobFilters();
      return <button onClick={() => { update({ city: "Mountain View" }); update({ sort: "title" }); }}>Two edits</button>;
    }
    render(<MemoryRouter initialEntries={["/jobs?company=Kodiak&country=US&page=2"]}><FastEdits /><RouteProbe /></MemoryRouter>);
    await userEvent.setup().click(screen.getByRole("button", { name: "Two edits" }));
    expect(screen.getByTestId("route")).toHaveTextContent("/jobs?company=Kodiak&country=US&city=Mountain+View&sort=title");
  });

  it("ignores old job and option responses after conditions are cleared", async () => {
    const original = fetch.getMockImplementation();
    const pending = [];
    fetch.mockImplementation(async (input, options) => {
      const url = new URL(input, "http://localhost");
      if (url.searchParams.get("company") === "Kodiak") {
        return new Promise(resolve => pending.push({ resolve, path: url.pathname, signal: options.signal }));
      }
      return original(input);
    });
    const user = userEvent.setup(); mount();
    await screen.findByRole("option", { name: "Germany (1)" });
    await select(user, "Filter by company", "Kodiak");
    await waitFor(() => expect(pending).toHaveLength(2));
    expect(screen.getByLabelText("Filter by country")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(screen.getByLabelText("Filter by country")).not.toBeDisabled());
    expect(pending.every(item => item.signal.aborted)).toBe(true);
    await act(async () => {
      for (const item of pending) item.resolve({ ok: true, json: async () => item.path === "/api/job-facets"
        ? { data: { ...facetFixture(), country: [{ value: "US", count: 1 }] } }
        : { data: [{ ...job, title: "Obsolete response" }], pagination: { total: 1, totalPages: 1 } } });
    });
    expect(screen.getByRole("option", { name: "Germany (1)" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Obsolete response" })).not.toBeInTheDocument();
  });
});
