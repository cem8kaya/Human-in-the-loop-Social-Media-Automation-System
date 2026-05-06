"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { fetchTrends, triggerDiscovery, generateForTrend, type Trend } from "@/lib/api";
import { RefreshCw, Sparkles } from "lucide-react";
import { format } from "date-fns";

const SOURCE_COLORS: Record<string, string> = {
  reddit: "bg-orange-100 text-orange-700",
  twitter: "bg-sky-100 text-sky-700",
  tiktok: "bg-pink-100 text-pink-700",
};

const VIRAL_FORMATS = ["curiosity_gap", "controversy", "built_in_x_days", "nobody_knows"];

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [selectedFormat, setSelectedFormat] = useState("curiosity_gap");
  const [filter, setFilter] = useState("");

  const load = () => {
    setLoading(true);
    fetchTrends()
      .then(setTrends)
      .catch(() => setMsg("Failed to load trends"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const discover = async () => {
    setLoading(true);
    setMsg("");
    try {
      await triggerDiscovery();
      setMsg("Discovery queued. Refreshing in 5s...");
      setTimeout(() => { load(); setMsg(""); }, 5000);
    } catch {
      setMsg("Discovery failed — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const generate = async (id: number) => {
    setGenerating(id);
    setMsg("");
    try {
      await generateForTrend(id, selectedFormat);
      setMsg(`Content generation queued for trend #${id}. Check Review Queue.`);
    } catch {
      setMsg("Generation failed");
    } finally {
      setGenerating(null);
    }
  };

  const filtered = trends.filter((t) =>
    !filter || t.topic.toLowerCase().includes(filter.toLowerCase()) || t.source.includes(filter.toLowerCase())
  );

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <h1 className="text-2xl font-bold text-slate-800">Trending Topics</h1>
          <div className="flex gap-2 flex-wrap">
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              {VIRAL_FORMATS.map((f) => (
                <option key={f} value={f}>{f.replace(/_/g, " ")}</option>
              ))}
            </select>
            <button
              onClick={discover}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
              Discover Trends
            </button>
          </div>
        </div>

        <input
          type="text"
          placeholder="Filter topics..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-full mb-4"
        />

        {msg && <p className="text-sm text-blue-600 bg-blue-50 rounded-lg px-4 py-2 mb-4">{msg}</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.length === 0 && !loading && (
            <p className="text-slate-500 col-span-3 text-center py-12">
              No trends yet. Click &ldquo;Discover Trends&rdquo; to fetch them.
            </p>
          )}
          {filtered.map((t) => (
            <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SOURCE_COLORS[t.source] ?? "bg-gray-100 text-gray-600"}`}>
                  {t.source}
                </span>
                <span className="text-xs text-slate-400">{format(new Date(t.created_at), "MMM d")}</span>
              </div>
              <p className="text-sm font-medium text-slate-800 leading-snug line-clamp-3">{t.topic}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <div className="h-1.5 w-24 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.round(t.score * 100)}%` }} />
                  </div>
                  <span className="text-xs text-slate-400">{Math.round(t.score * 100)}%</span>
                </div>
                <button
                  onClick={() => generate(t.id)}
                  disabled={generating === t.id}
                  className="flex items-center gap-1 text-xs bg-slate-800 text-white px-3 py-1.5 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  <Sparkles size={12} />
                  {generating === t.id ? "..." : "Generate"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
