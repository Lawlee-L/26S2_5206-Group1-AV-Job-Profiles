const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function getInsights({ signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/insights`, { signal });
  if (!response.ok) throw new Error("Analysis could not be loaded. Check the backend connection and published release, then retry.");
  return (await response.json()).data;
}
