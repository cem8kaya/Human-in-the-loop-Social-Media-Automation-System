"use client";
import { useState } from "react";
import { format } from "date-fns";
import { CheckCircle, XCircle, Edit3, Clock, Send } from "lucide-react";
import StatusBadge from "./StatusBadge";
import type { Post } from "@/lib/api";
import { reviewPost, schedulePost, publishNow, deletePost } from "@/lib/api";

interface Props {
  post: Post;
  onRefresh: () => void;
}

const PLATFORMS = ["twitter", "instagram", "tiktok"];

export default function PostCard({ post, onRefresh }: Props) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ hook: post.hook, script: post.script, caption: post.caption, hashtags: post.hashtags });
  const [platform, setPlatform] = useState(post.platform);
  const [scheduledAt, setScheduledAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handle = async (fn: () => Promise<unknown>) => {
    setLoading(true);
    setError("");
    try {
      await fn();
      onRefresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const approve = () => handle(() => reviewPost(post.id, { action: "approve", platform }));
  const reject = () => handle(() => reviewPost(post.id, { action: "reject", rejection_reason: "Rejected by reviewer" }));
  const saveEdit = () =>
    handle(() => reviewPost(post.id, { action: "edit", ...form, platform }));
  const schedule = () => {
    if (!scheduledAt) { setError("Pick a date/time first"); return; }
    handle(() => schedulePost(post.id, new Date(scheduledAt).toISOString()));
  };
  const publish = () => handle(() => publishNow(post.id));
  const remove = () => handle(() => deletePost(post.id));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={post.status} />
          <span className="text-xs text-slate-400 uppercase font-medium">{post.platform}</span>
          <span className="text-xs text-slate-400">v{post.variation_index + 1}</span>
        </div>
        <span className="text-xs text-slate-400 shrink-0">{format(new Date(post.created_at), "MMM d, HH:mm")}</span>
      </div>

      {/* Content */}
      {editing ? (
        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold text-slate-500 uppercase">Hook</label>
          <input
            className="border rounded px-3 py-1.5 text-sm w-full"
            value={form.hook}
            onChange={(e) => setForm({ ...form, hook: e.target.value })}
          />
          <label className="text-xs font-semibold text-slate-500 uppercase">Caption</label>
          <textarea
            className="border rounded px-3 py-1.5 text-sm w-full"
            rows={3}
            value={form.caption}
            onChange={(e) => setForm({ ...form, caption: e.target.value })}
          />
          <label className="text-xs font-semibold text-slate-500 uppercase">Hashtags</label>
          <input
            className="border rounded px-3 py-1.5 text-sm w-full"
            value={form.hashtags}
            onChange={(e) => setForm({ ...form, hashtags: e.target.value })}
          />
          <label className="text-xs font-semibold text-slate-500 uppercase">Script</label>
          <textarea
            className="border rounded px-3 py-1.5 text-sm w-full"
            rows={5}
            value={form.script}
            onChange={(e) => setForm({ ...form, script: e.target.value })}
          />
        </div>
      ) : (
        <>
          <p className="font-semibold text-slate-800 text-base leading-snug">{post.hook}</p>
          <p className="text-sm text-slate-600 line-clamp-3">{post.caption}</p>
          <p className="text-xs text-blue-500">{post.hashtags}</p>
        </>
      )}

      {/* Platform selector */}
      {(post.status === "generated" || post.status === "pending_review" || editing) && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Platform:</span>
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`text-xs px-2 py-1 rounded-full border transition ${
                platform === p ? "bg-blue-600 text-white border-blue-600" : "border-slate-300 text-slate-600 hover:border-blue-400"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Schedule input */}
      {post.status === "approved" && (
        <div className="flex items-center gap-2">
          <input
            type="datetime-local"
            className="border rounded px-2 py-1 text-sm flex-1"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
          />
          <button onClick={schedule} disabled={loading} className="flex items-center gap-1 text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-700 disabled:opacity-50">
            <Clock size={13} /> Schedule
          </button>
          <button onClick={publish} disabled={loading} className="flex items-center gap-1 text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 disabled:opacity-50">
            <Send size={13} /> Now
          </button>
        </div>
      )}

      {/* Rejection reason */}
      {post.status === "rejected" && post.rejection_reason && (
        <p className="text-xs text-red-500 italic">{post.rejection_reason}</p>
      )}

      {/* Scheduled time */}
      {post.scheduled_at && post.status === "scheduled" && (
        <p className="text-xs text-purple-600">Scheduled: {format(new Date(post.scheduled_at), "MMM d, yyyy HH:mm")}</p>
      )}

      {/* Posted time */}
      {post.posted_at && (
        <p className="text-xs text-green-600">Posted: {format(new Date(post.posted_at), "MMM d, yyyy HH:mm")}</p>
      )}

      {error && <p className="text-xs text-red-500">{error}</p>}

      {/* Action buttons */}
      {(post.status === "generated" || post.status === "pending_review") && (
        <div className="flex gap-2 flex-wrap pt-1">
          {!editing ? (
            <>
              <button onClick={approve} disabled={loading} className="flex items-center gap-1 text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                <CheckCircle size={13} /> Approve
              </button>
              <button onClick={() => setEditing(true)} className="flex items-center gap-1 text-xs border border-slate-300 text-slate-700 px-3 py-1.5 rounded-lg hover:border-blue-400">
                <Edit3 size={13} /> Edit
              </button>
              <button onClick={reject} disabled={loading} className="flex items-center gap-1 text-xs border border-red-300 text-red-600 px-3 py-1.5 rounded-lg hover:border-red-500 disabled:opacity-50">
                <XCircle size={13} /> Reject
              </button>
            </>
          ) : (
            <>
              <button onClick={saveEdit} disabled={loading} className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                Save & Approve
              </button>
              <button onClick={() => setEditing(false)} className="text-xs border border-slate-300 text-slate-600 px-3 py-1.5 rounded-lg">
                Cancel
              </button>
            </>
          )}
          <button onClick={remove} disabled={loading} className="ml-auto text-xs text-slate-400 hover:text-red-500">
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
