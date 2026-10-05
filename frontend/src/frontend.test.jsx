// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import React from "react";
import { describe, it, expect, afterEach } from "vitest";
import {
  render,
  screen,
  within,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";
import { jobs } from "./data/jobs";

afterEach(() => {
  cleanup();
});

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );

/* =========================================================
   JOB DATA
   ========================================================= */

describe("job data used by the UI", () => {
  it("gives every job the fields the pages and backend contract rely on", () => {
    const required = [
      "id",
      "company",
      "title",
      "location",
      "type",
      "level",
      "date",
      "description",
      "originalUrl",
    ];

    jobs.forEach((job) => {
      required.forEach((field) =>
        expect(
          job[field],
          `${job.id}.${field}`
        ).toBeTruthy()
      );

      expect(Array.isArray(job.skills)).toBe(true);
    });
  });

  it("uses unique ids so /jobs/:id routes are unambiguous", () => {
    const ids = jobs.map((job) => job.id);

    expect(new Set(ids).size).toBe(ids.length);
  });
});

/* =========================================================
   HOME PAGE
   ========================================================= */

describe("Home page", () => {
  it("shows the hero message and a Browse Jobs call to action linking to /jobs", () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", {
        level: 1,
      })
    ).toHaveTextContent(/Discover Autonomous/i);

    expect(
      screen.getByRole("link", {
        name: /Browse Jobs/i,
      })
    ).toHaveAttribute("href", "/jobs");
  });
});

/* =========================================================
   JOBS PAGE
   ========================================================= */

describe("Jobs page", () => {
  it("lists every job with its title, company and posted date", () => {
    renderAt("/jobs");

    jobs.forEach((job) => {
      expect(
        screen.getByRole("heading", {
          name: job.title,
        })
      ).toBeInTheDocument();
    });

    const first = screen
      .getByRole("heading", {
        name: jobs[0].title,
      })
      .closest("a");

    expect(first).not.toBeNull();

    expect(
      within(first).getByText(
        jobs[0].company,
        {
          selector: "strong",
        }
      )
    ).toBeInTheDocument();

    expect(
      within(first).getByText(jobs[0].date)
    ).toBeInTheDocument();
  });

  it("links each card to its details route", () => {
    renderAt("/jobs");

    const card = screen
      .getByRole("heading", {
        name: jobs[0].title,
      })
      .closest("a");

    expect(card).not.toBeNull();

    expect(card).toHaveAttribute(
      "href",
      `/jobs/${jobs[0].id}`
    );
  });

  it("filters the list as the user types in the search box", async () => {
    const user = userEvent.setup();

    renderAt("/jobs");

    await user.type(
      screen.getByPlaceholderText(
        /Search by job title/i
      ),
      "nvidia"
    );

    const expected = jobs.filter((job) =>
      [
        job.title,
        job.company,
        job.location,
        ...job.skills,
      ]
        .join(" ")
        .toLowerCase()
        .includes("nvidia")
    );

    expect(expected.length).toBeGreaterThan(0);

    expect(expected.length).toBeLessThan(
      jobs.length
    );

    /* Check that matching jobs are displayed */
    expected.forEach((job) => {
      expect(
        screen.getByRole("heading", {
          name: job.title,
        })
      ).toBeInTheDocument();
    });

    /* Check that non-matching jobs are removed */
    const notExpected = jobs.filter(
      (job) =>
        !expected.some(
          (expectedJob) =>
            expectedJob.id === job.id
        )
    );

    notExpected.forEach((job) => {
      expect(
        screen.queryByRole("heading", {
          name: job.title,
        })
      ).not.toBeInTheDocument();
    });
  });

  it("shows no job cards when nothing matches the search", async () => {
    const user = userEvent.setup();

    renderAt("/jobs");

    await user.type(
      screen.getByPlaceholderText(
        /Search by job title/i
      ),
      "zzzz-no-match"
    );

    /*
      Check specifically for job titles instead of
      checking every h3 on the page.

      The shared Footer may also contain headings,
      so counting all h3 elements is unreliable.
    */
    jobs.forEach((job) => {
      expect(
        screen.queryByRole("heading", {
          name: job.title,
        })
      ).not.toBeInTheDocument();
    });
  });
});

/* =========================================================
   JOB DETAILS PAGE
   ========================================================= */

describe("Job Details page", () => {
  it("renders the selected job and a Back to Jobs link", () => {
    renderAt(`/jobs/${jobs[1].id}`);

    expect(
      screen.getAllByText(jobs[1].title).length
    ).toBeGreaterThan(0);

    expect(
      screen.getByRole("link", {
        name: /Back to Jobs/i,
      })
    ).toHaveAttribute("href", "/jobs");
  });

  it("shows the selected job posting date", () => {
    const selectedJob = jobs[1];

    renderAt(`/jobs/${selectedJob.id}`);

    expect(
      screen.getByText(selectedJob.date)
    ).toBeInTheDocument();
  });
});