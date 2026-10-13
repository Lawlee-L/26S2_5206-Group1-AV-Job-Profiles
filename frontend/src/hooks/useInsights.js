import { useEffect, useState } from "react";
import { getInsights } from "../api/insights";

export default function useInsights() {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, loading: true, error: "" });
    getInsights({ signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ data, loading: false, error: "" }); })
      .catch((error) => { if (!controller.signal.aborted) setState({ data: null, loading: false, error: error.message }); });
    return () => controller.abort();
  }, [attempt]);
  return { ...state, retry: () => setAttempt((value) => value + 1) };
}
