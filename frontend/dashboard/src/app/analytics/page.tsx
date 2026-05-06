"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { fetchSummary, fetchTopPosts, type Summary } from "@/lib/api";
import { format } from "date-fns";

interface TopPost {
  post_id: number;
  platform: string;
  hook: string;
  caption: string;
  variation_index: number;
  views: number;
  likes: number;
  engagement_score: number;
  content_score: number;
}

function EngagementBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.min(score * 100, 100)}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-12 text-right">{(score * 100).toFixed(1)}%</span>
    </div>
  );
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [top, setTop] = useState<TopPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSummary(), fetchTopPosts(15)])
      .then(([s, t]) => { setSummary(s); setTop(t); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-slate-800 mb-8">Analytics</h1>

        {loading && <p className="text-slate-500 text-center py-12">Loading analytics...</p>}

        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
            {[
              { label: "Posted", value: summary.total_posted },
              { label: "Views", value: summary.total_views.toLocaleString() },
              { label: "Likes", value: summary.total_likes.toLocaleString() },
              { label: "Comments", value: summary.total_comments.toLocaleString() },
              { label: "Shares", value: summary.total_shares.toLocaleString() },
              { label: "Avg Engagement", value: `${(summary.avg_engagement_score * 100).toFixed(2)}%` },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-4 text-center shadow-sm">
                <p className="text-xl font-bold text-slate-800">{s.value}</p>
                <p className="text-xs text-slate-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {summary?.best_variation != null && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-4 mb-8 text-sm text-green-800">
            <strong>A/B Winner:</strong> Variation {summary.best_variation + 1} has the best average engagement score ({(( summary.best_variation_avg_score ?? 0) * 100).toFixed(2)}%).
            Use this format more in content generation.
          </div>
        )}

        <h2 className="text-lg font-semibold text-slate-700 mb-4">Top Performing Posts</h2>
        {top.length === 0 && !loading && (
          <p className="text-slate-400 text-sm">No posted content yet. Posts will appear here after publishing.</p>
        )}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Hook</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Platform</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Var</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Views</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Likes</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase w-40">Engagement</th>
              </tr>
            </thead>
            <tbody>
              {top.map((p, i) => (
                <tr key={p.post_id} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                  <td className="px-4 py-3 text-slate-800 max-w-xs truncate">{p.hook}</td>
                  <td className="px-4 py-3 text-slate-500 capitalize">{p.platform}</td>
                  <td className="px-4 py-3 text-slate-500">v{p.variation_index + 1}</td>
                  <td className="px-4 py-3 text-right text-slate-700">{p.views.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-slate-700">{p.likes.toLocaleString()}</td>
                  <td className="px-4 py-3 w-40"><EngagementBar score={p.engagement_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}
