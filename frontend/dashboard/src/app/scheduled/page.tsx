"use client";
import { useCallback, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import PostCard from "@/components/PostCard";
import { fetchPosts, type Post } from "@/lib/api";

export default function ScheduledPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetchPosts({ status: "scheduled", page_size: 50 })
      .then((r) => setPosts(r.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Scheduled Posts</h1>
        {loading && <p className="text-slate-500 text-sm text-center py-12">Loading...</p>}
        {!loading && posts.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p className="text-lg">No scheduled posts</p>
            <p className="text-sm mt-2">Approve posts in the Review Queue, then schedule them.</p>
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {posts.map((p) => <PostCard key={p.id} post={p} onRefresh={load} />)}
        </div>
      </main>
    </>
  );
}
