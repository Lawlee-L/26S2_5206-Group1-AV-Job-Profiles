export const companies = [
  { name: "NVIDIA", short: "NVIDIA", className: "logo-nvidia" },
  { name: "Mobileye", short: "m", className: "logo-mobileye" },
  { name: "Motional", short: "M", className: "logo-motional" },
  { name: "Pony.ai", short: "pony.ai", className: "logo-pony" },
  { name: "Nuro", short: "nuro", className: "logo-nuro" },
  { name: "Momenta", short: "M", className: "logo-momenta" },
  { name: "Plus AI", short: "Plus", className: "logo-plus" }
];

export const jobs = [
  {
    id: "nvidia-perception",
    company: "NVIDIA",
    title: "Senior Perception Software Engineer",
    location: "Santa Clara, CA, USA",
    type: "Full-time",
    level: "Senior",
    date: "Aug 20, 2026",
    salary: "$150,000 - $200,000 per year",
    experience: "5+ years",
    education: "Bachelor's or Master's degree",
    skills: ["C++", "Python", "CUDA", "Computer Vision", "Deep Learning", "LiDAR", "ROS2"],
    description:
      "NVIDIA is seeking a Senior Perception Software Engineer to join our Autonomous Machines team. You will work on developing cutting-edge perception systems for self-driving vehicles.",
    responsibilities: [
      "Design and implement perception algorithms for AV systems",
      "Work with LiDAR, camera, and radar data",
      "Optimize performance for real-time systems",
      "Collaborate with cross-functional teams"
    ],
    requirements: [
      "5+ years of experience in C++ software development",
      "Strong knowledge of computer vision and deep learning",
      "Experience with LiDAR data processing",
      "Bachelor's or Master's degree in Computer Science or a related field"
    ],
    originalUrl: "https://www.nvidia.com/en-us/about-nvidia/careers/"
  },
  {
    id: "mobileye-driving",
    company: "Mobileye",
    title: "Autonomous Driving Software Engineer",
    location: "Jerusalem, Israel",
    type: "Full-time",
    level: "Mid-Senior",
    date: "Aug 19, 2026",
    salary: "Competitive",
    experience: "3+ years",
    education: "Bachelor's degree",
    skills: ["C++", "Python", "ROS2", "Linux"],
    description: "Build software systems for autonomous driving and perception platforms.",
    responsibilities: ["Develop AV software modules", "Integrate perception components", "Write production-quality C++"],
    requirements: ["Strong C++", "Linux experience", "Understanding of robotics or AV systems"],
    originalUrl: "https://careers.mobileye.com/"
  },
  {
    id: "motional-ml",
    company: "Motional",
    title: "Machine Learning Engineer",
    location: "Boston, MA, USA",
    type: "Full-time",
    level: "Mid-Senior",
    date: "Aug 18, 2026",
    salary: "$140,000 - $190,000 per year",
    experience: "3+ years",
    education: "Bachelor's or Master's degree",
    skills: ["Python", "PyTorch", "Deep Learning"],
    description: "Develop machine learning models for autonomous driving applications.",
    responsibilities: ["Train ML models", "Evaluate datasets", "Work with AV research teams"],
    requirements: ["Python", "PyTorch", "Machine learning fundamentals"],
    originalUrl: "https://motional.com/careers"
  },
  {
    id: "nuro-robotics",
    company: "Nuro",
    title: "Robotics Software Engineer",
    location: "Mountain View, CA, USA",
    type: "Full-time",
    level: "Mid",
    date: "Aug 18, 2026",
    salary: "$145,000 - $195,000 per year",
    experience: "3+ years",
    education: "Bachelor's degree",
    skills: ["C++", "ROS2", "Linux", "Robotics"],
    description: "Work on autonomy software for delivery vehicles.",
    responsibilities: ["Develop robotics software", "Test autonomy features", "Improve runtime performance"],
    requirements: ["C++", "Robotics knowledge", "Linux"],
    originalUrl: "https://www.nuro.ai/careers"
  },
  {
    id: "momenta-localization",
    company: "Momenta",
    title: "Localization Engineer",
    location: "Beijing, China",
    type: "Full-time",
    level: "Senior",
    date: "Aug 17, 2026",
    salary: "Competitive",
    experience: "4+ years",
    education: "Bachelor's degree",
    skills: ["C++", "Python", "SLAM", "LiDAR"],
    description: "Develop localization and mapping algorithms for autonomous vehicles.",
    responsibilities: ["Build localization algorithms", "Fuse sensor data", "Optimize SLAM pipelines"],
    requirements: ["SLAM", "C++", "LiDAR knowledge"],
    originalUrl: "#"
  },
  {
    id: "pony-planning",
    company: "Pony.ai",
    title: "Planning Engineer",
    location: "Fremont, CA, USA",
    type: "Full-time",
    level: "Senior",
    date: "Aug 16, 2026",
    salary: "$150,000 - $210,000 per year",
    experience: "5+ years",
    education: "Bachelor's degree",
    skills: ["C++", "Planning", "Autonomous Driving"],
    description: "Design motion planning algorithms for autonomous vehicles.",
    responsibilities: ["Create planning algorithms", "Test scenarios", "Collaborate with controls teams"],
    requirements: ["C++", "Planning experience", "AV domain knowledge"],
    originalUrl: "https://www.pony.ai/careers"
  },
  {
    id: "plus-fullstack",
    company: "Plus AI",
    title: "Full Stack Engineer",
    location: "Palo Alto, CA, USA",
    type: "Full-time",
    level: "Mid",
    date: "Aug 15, 2026",
    salary: "$130,000 - $175,000 per year",
    experience: "3+ years",
    education: "Bachelor's degree",
    skills: ["TypeScript", "React", "Node.js", "AWS"],
    description: "Build internal and customer-facing tools for autonomous trucking technology.",
    responsibilities: ["Build React interfaces", "Develop APIs", "Work with cloud services"],
    requirements: ["React", "Node.js", "Cloud experience"],
    originalUrl: "https://plus.ai/careers"
  }
];

export function getJobById(id) {
  return jobs.find((job) => job.id === id);
}

export function getCompany(name) {
  return companies.find((company) => company.name === name) || companies[0];
}
