// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import React from "react";

import {
  describe,
  it,
  expect,
  afterEach,
  beforeEach,
  vi,
} from "vitest";

import {
  render,
  screen,
  within,
  cleanup,
  waitFor,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

import {
  getJobs,
  getJob,
  getCompanies,
  getSkills,
} from "./api/jobs";

/* =========================================================
   MOCK API
   ========================================================= */

vi.mock("./api/jobs", () => ({
  getJobs: vi.fn(),
  getJob: vi.fn(),
  getCompanies: vi.fn(),
  getSkills: vi.fn(),
}));

/* =========================================================
   TEST DATA
   Same shape expected by the current frontend
   ========================================================= */

const mockJobs = [
  {
    sourceKey: "greenhouse|kodiak|id:1001",
    company: "Kodiak",
    title: "Autonomous Driving Software Engineer",
    location: "Mountain View, CA, United States",
    country: "United States",
    remoteType: "onsite",
    seniority: "mid",
    postedDate: "Aug 19, 2026",
    jobUrl: "https://example.com/kodiak-job",

    description:
      "Develop software for autonomous driving systems.",

    roleSummary:
      "Build autonomous driving software.",

    responsibilities: [
      "Develop autonomous vehicle software.",
      "Test autonomous driving systems.",
    ],

    requirements: [
      "Experience with software engineering.",
      "Knowledge of robotics.",
    ],

    skills: [
      {
        name: "Python",
        type: "technical",
        confidence: 0.95,
        rank: 1,
      },
      {
        name: "C++",
        type: "technical",
        confidence: 0.9,
        rank: 2,
      },
    ],
  },

  {
    sourceKey: "greenhouse|mobileye|id:1002",
    company: "Mobileye",
    title: "Computer Vision Engineer",
    location: "New York, NY, United States",
    country: "United States",
    remoteType: "hybrid",
    seniority: "senior",
    postedDate: "Aug 20, 2026",
    jobUrl: "https://example.com/mobileye-job",

    description:
      "Work on computer vision technology for autonomous vehicles.",

    roleSummary:
      "Develop perception and computer vision systems.",

    responsibilities: [
      "Design computer vision algorithms.",
      "Test perception systems.",
    ],

    requirements: [
      "Experience with computer vision.",
      "Experience with machine learning.",
    ],

    skills: [
      {
        name: "Computer Vision",
        type: "technical",
        confidence: 0.98,
        rank: 1,
      },
      {
        name: "Python",
        type: "technical",
        confidence: 0.93,
        rank: 2,
      },
    ],
  },

  {
    sourceKey: "greenhouse|nvidia|id:1003",
    company: "NVIDIA",
    title: "Autonomous Vehicle AI Engineer",
    location: "Santa Clara, CA, United States",
    country: "United States",
    remoteType: "onsite",
    seniority: "senior",
    postedDate: "Aug 21, 2026",
    jobUrl: "https://example.com/nvidia-job",

    description:
      "Develop AI systems for autonomous vehicle applications.",

    roleSummary:
      "Build AI technology for autonomous vehicles.",

    responsibilities: [
      "Develop machine learning models.",
      "Build AI systems for autonomous vehicles.",
    ],

    requirements: [
      "Experience with artificial intelligence.",
      "Experience with machine learning.",
    ],

    skills: [
      {
        name: "Machine Learning",
        type: "technical",
        confidence: 0.99,
        rank: 1,
      },
      {
        name: "Python",
        type: "technical",
        confidence: 0.96,
        rank: 2,
      },
    ],
  },
];

/* =========================================================
   COMPANY MOCK DATA
   ========================================================= */

const mockCompanies = [
  {
    name: "Kodiak",
    jobCount: 58,
  },
  {
    name: "Mobileye",
    jobCount: 111,
  },
  {
    name: "NVIDIA",
    jobCount: 50,
  },
];

/* =========================================================
   SKILL MOCK DATA
   ========================================================= */

const mockSkills = [
  {
    name: "Python",
  },
  {
    name: "C++",
  },
  {
    name: "Machine Learning",
  },
];

/* =========================================================
   API RESPONSE HELPER
   ========================================================= */

function createJobsResponse(data = mockJobs) {
  return {
    data,

    pagination: {
      page: 1,
      pageSize: 20,
      total: data.length,
      totalPages: 1,
    },
  };
}

/* =========================================================
   DATE FORMAT HELPER

   Frontend displays:
   Aug 19, 2026 -> 19 Aug 2026
   ========================================================= */

function formatTestDate(date) {
  return new Date(date).toLocaleDateString(
    "en-AU",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  );
}

/* =========================================================
   SETUP
   ========================================================= */

beforeEach(() => {
  vi.clearAllMocks();

  getJobs.mockResolvedValue(
    createJobsResponse()
  );

  getCompanies.mockResolvedValue(
    mockCompanies
  );

  getSkills.mockResolvedValue(
    mockSkills
  );

  getJob.mockImplementation(
    async (sourceKey) => {
      const job = mockJobs.find(
        (item) =>
          item.sourceKey === sourceKey
      );

      return {
        data: job || mockJobs[0],
      };
    }
  );
});

afterEach(() => {
  cleanup();
});

/* =========================================================
   RENDER HELPER
   ========================================================= */

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );

/* =========================================================
   API DATA SHAPE
   ========================================================= */

describe("job data used by the UI", () => {
  it("matches the backend API fields used by the frontend", () => {
    const required = [
      "sourceKey",
      "company",
      "title",
      "location",
      "postedDate",
      "jobUrl",
      "description",
    ];

    mockJobs.forEach((job) => {
      required.forEach((field) => {
        expect(
          job[field],
          `${job.sourceKey}.${field}`
        ).toBeTruthy();
      });

      expect(
        Array.isArray(job.skills)
      ).toBe(true);

      expect(
        Array.isArray(job.responsibilities)
      ).toBe(true);

      expect(
        Array.isArray(job.requirements)
      ).toBe(true);
    });
  });

  it("uses unique sourceKeys for job detail routes", () => {
    const sourceKeys = mockJobs.map(
      (job) => job.sourceKey
    );

    expect(
      new Set(sourceKeys).size
    ).toBe(sourceKeys.length);
  });
});

/* =========================================================
   HOME PAGE
   ========================================================= */

describe("Home page", () => {
  it("shows the hero message and Browse Jobs link", async () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", {
        level: 1,
      })
    ).toHaveTextContent(
      /Discover Autonomous/i
    );

    expect(
      screen.getByRole("link", {
        name: /Browse Jobs/i,
      })
    ).toHaveAttribute(
      "href",
      "/jobs"
    );

    await waitFor(() => {
      expect(
        getJobs
      ).toHaveBeenCalled();
    });
  });
});

/* =========================================================
   JOBS PAGE
   ========================================================= */

describe("Jobs page", () => {
  it("lists jobs returned by the API", async () => {
    renderAt("/jobs");

    for (const job of mockJobs) {
      expect(
        await screen.findByRole(
          "heading",
          {
            name: job.title,
          }
        )
      ).toBeInTheDocument();
    }

    const first = screen
      .getByRole("heading", {
        name: mockJobs[0].title,
      })
      .closest("a");

    expect(first).not.toBeNull();

    expect(
      within(first).getByText(
        mockJobs[0].company,
        {
          selector: "strong",
        }
      )
    ).toBeInTheDocument();

    expect(
      within(first).getByText(
        formatTestDate(
          mockJobs[0].postedDate
        )
      )
    ).toBeInTheDocument();
  });

  it("links each job card using its encoded sourceKey", async () => {
    renderAt("/jobs");

    const heading =
      await screen.findByRole(
        "heading",
        {
          name: mockJobs[0].title,
        }
      );

    const card =
      heading.closest("a");

    expect(card).not.toBeNull();

    expect(card).toHaveAttribute(
      "href",
      `/jobs/${encodeURIComponent(
        mockJobs[0].sourceKey
      )}`
    );
  });

  it("sends search text to the jobs API", async () => {
    const user =
      userEvent.setup();

    getJobs.mockImplementation(
      async ({ q = "" } = {}) => {
        const search =
          q.trim().toLowerCase();

        if (!search) {
          return createJobsResponse(
            mockJobs
          );
        }

        const filtered =
          mockJobs.filter((job) => {
            const searchable = [
              job.title,
              job.company,
              job.location,
              ...job.skills.map(
                (skill) => skill.name
              ),
            ]
              .join(" ")
              .toLowerCase();

            return searchable.includes(
              search
            );
          });

        return createJobsResponse(
          filtered
        );
      }
    );

    renderAt("/jobs");

    await screen.findByRole(
      "heading",
      {
        name: mockJobs[0].title,
      }
    );

    const searchBox =
      screen.getByPlaceholderText(
        /Search by job title/i
      );

    await user.type(
      searchBox,
      "nvidia"
    );

    await waitFor(
      () => {
        expect(
          getJobs
        ).toHaveBeenCalledWith(
          expect.objectContaining({
            q: "nvidia",
          })
        );
      },
      {
        timeout: 2000,
      }
    );

    expect(
      await screen.findByRole(
        "heading",
        {
          name:
            "Autonomous Vehicle AI Engineer",
        }
      )
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.queryByRole(
          "heading",
          {
            name:
              "Computer Vision Engineer",
          }
        )
      ).not.toBeInTheDocument();
    });
  });

  it("shows no job cards when the API returns no search matches", async () => {
    const user =
      userEvent.setup();

    getJobs.mockImplementation(
      async ({ q = "" } = {}) => {
        if (
          q
            .toLowerCase()
            .includes(
              "zzzz-no-match"
            )
        ) {
          return createJobsResponse(
            []
          );
        }

        return createJobsResponse(
          mockJobs
        );
      }
    );

    renderAt("/jobs");

    await screen.findByRole(
      "heading",
      {
        name: mockJobs[0].title,
      }
    );

    await user.type(
      screen.getByPlaceholderText(
        /Search by job title/i
      ),
      "zzzz-no-match"
    );

    await waitFor(
      () => {
        expect(
          getJobs
        ).toHaveBeenCalledWith(
          expect.objectContaining({
            q: "zzzz-no-match",
          })
        );
      },
      {
        timeout: 2000,
      }
    );

    await waitFor(() => {
      mockJobs.forEach((job) => {
        expect(
          screen.queryByRole(
            "heading",
            {
              name: job.title,
            }
          )
        ).not.toBeInTheDocument();
      });
    });
  });
});

/* =========================================================
   JOB DETAILS PAGE
   ========================================================= */

describe("Job Details page", () => {
  it("renders the selected API job and Back to Jobs link", async () => {
    const selectedJob =
      mockJobs[1];

    renderAt(
      `/jobs/${encodeURIComponent(
        selectedJob.sourceKey
      )}`
    );

    expect(
      await screen.findByRole(
        "heading",
        {
          name: selectedJob.title,
        }
      )
    ).toBeInTheDocument();

    expect(
      getJob
    ).toHaveBeenCalledWith(
      selectedJob.sourceKey
    );

    expect(
      screen.getByRole("link", {
        name: /Back to Jobs/i,
      })
    ).toHaveAttribute(
      "href",
      "/jobs"
    );
  });

  it("shows the selected job posting date", async () => {
    const selectedJob =
      mockJobs[1];

    renderAt(
      `/jobs/${encodeURIComponent(
        selectedJob.sourceKey
      )}`
    );

    expect(
      await screen.findByText(
        formatTestDate(
          selectedJob.postedDate
        )
      )
    ).toBeInTheDocument();
  });
});