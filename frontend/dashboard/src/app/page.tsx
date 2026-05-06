"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { fetchSummary, triggerDemoWorkflow, type Summary } from "@/lib/api";
import { TrendingUp, FileText, CheckCircle, Send, BarChart2, Zap } from "lucide-react";

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-start gap-4 shadow-sm">
      <div className="p-2 bg-blue-50 rounded-lg text-blue-600">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-sm text-slate-500">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [demoMsg, setDemoMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSummary().then(setSummary).catch(() => {});
  }, []);

  const runDemo = async () => {
    setLoading(true);
    setDemoMsg("");
    try {
      const r = await triggerDemoWorkflow();
      setDemoMsg("Demo workflow started! Check Trends and Review Queue in 10–30s.");
      console.log(r);
    } catch {
      setDemoMsg("Could not connect to API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
            <p className="text-slate-500 text-sm mt-1">Human-in-the-loop social media automation for mobile apps & games</p>
          </div>
          <button
            onClick={runDemo}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            <Zap size={16} />
            {loading ? "Starting..." : "Run Demo Workflow"}
          </button>
        </div>

        {demoMsg && (
          <div className="mb-6 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg px-4 py-3 text-sm">
            {demoMsg}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-10">
          <StatCard icon={<Send size={20} />} label="Total Posted" value={summary?.total_posted ?? "—"} />
          <StatCard icon={<TrendingUp size={20} />} label="Total Views" value={summary?.total_views?.toLocaleString() ?? "—"} />
          <StatCard icon={<CheckCircle size={20} />} label="Total Likes" value={summary?.total_likes?.toLocaleString() ?? "—"} />
          <StatCard
            icon={<BarChart2 size={20} />}
            label="Avg Engagement"
            value={summary?.avg_engagement_score ? `${(summary.avg_engagement_score * 100).toFixed(2)}%` : "—"}
            sub={summary?.best_variation != null ? `Best: Variation ${summary.best_variation + 1}` : undefined}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: "/trends", icon: <TrendingUp size={24} />, title: "Trend Discovery", desc: "View trending topics from Reddit, TikTok & Twitter. Trigger generation." },
            { href: "/review", icon: <FileText size={24} />, title: "Review Queue", desc: "Approve, edit, or reject AI-generated posts before they go live." },
            { href: "/analytics", icon: <BarChart2 size={24} />, title: "Analytics", desc: "Track engagement and find your best-performing content formats." },
          ].map((card) => (
            <a
              key={card.href}
              href={card.href}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-400 hover:shadow-md transition group"
            >
              <div className="text-blue-600 mb-3">{card.icon}</div>
              <h3 className="font-semibold text-slate-800 group-hover:text-blue-600">{card.title}</h3>
              <p className="text-sm text-slate-500 mt-1">{card.desc}</p>
            </a>
          ))}
        </div>

        <div className="mt-10 bg-slate-800 rounded-xl p-6 text-white">
          <h2 className="font-bold text-lg mb-3">Status Flow</h2>
          <div className="flex flex-wrap gap-3 items-center text-sm">
            {["generated", "pending_review", "approved", "scheduled", "posted"].map((s, i, arr) => (
              <span key={s} className="flex items-center gap-2">
                <span className="bg-slate-700 px-3 py-1 rounded-full text-slate-200 capitalize">{s.replace("_", " ")}</span>
                {i < arr.length - 1 && <span className="text-slate-500">→</span>}
              </span>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
