"use client";
import { useCallback, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import PostCard from "@/components/PostCard";
import { fetchPosts, type Post } from "@/lib/api";

const STATUS_FILTERS = ["all", "generated", "pending_review", "approved", "rejected"];

export default function ReviewPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [status, setStatus] = useState("generated");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, unknown> = { page, page_size: 9 };
    if (status !== "all") params.status = status;
    fetchPosts(params)
      .then((r) => { setPosts(r.items); setTotalPages(r.pages); setTotal(r.total); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [status, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [status]);

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Review Queue</h1>
            <p className="text-slate-500 text-sm">{total} posts</p>
          </div>
          <div className="flex gap-1 flex-wrap">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition ${
                  status === s
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {loading && <p className="text-slate-500 text-sm text-center py-12">Loading...</p>}

        {!loading && posts.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p className="text-lg">No posts in &ldquo;{status.replace("_", " ")}&rdquo;</p>
            <p className="text-sm mt-2">Go to Trends and click Generate to create content.</p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {posts.map((p) => (
            <PostCard key={p.id} post={p} onRefresh={load} />
          ))}
        </div>

        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-8 h-8 rounded text-sm font-medium ${
                  p === page ? "bg-blue-600 text-white" : "bg-white border border-slate-300 text-slate-600 hover:border-blue-400"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
