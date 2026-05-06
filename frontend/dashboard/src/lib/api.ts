import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// ── Types ──────────────────────────────────────────────────────────────────

export interface Trend {
  id: number;
  source: string;
  topic: string;
  score: number;
  created_at: string;
}

export interface Post {
  id: number;
  trend_id: number | null;
  hook: string;
  script: string;
  caption: string;
  hashtags: string;
  platform: string;
  variation_index: number;
  status: string;
  rejection_reason: string | null;
  editor_notes: string | null;
  media_url: string | null;
  scheduled_at: string | null;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Analytics {
  id: number;
  post_id: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  clicks: number;
  engagement_score: number;
  content_score: number;
  fetched_at: string;
}

export interface Summary {
  total_posted: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  avg_engagement_score: number;
  best_variation: number | null;
  best_variation_avg_score: number | null;
}

export interface PaginatedPosts {
  items: Post[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── API helpers ────────────────────────────────────────────────────────────

export const fetchTrends = () => api.get<Trend[]>("/trends/").then((r) => r.data);
export const triggerDiscovery = () => api.post("/trends/discover").then((r) => r.data);
export const generateForTrend = (trendId: number, format?: string) =>
  api.post(`/trends/generate/${trendId}`, null, { params: { viral_format: format } }).then((r) => r.data);

export const fetchPosts = (params: Record<string, unknown>) =>
  api.get<PaginatedPosts>("/posts/", { params }).then((r) => r.data);

export const reviewPost = (postId: number, action: Record<string, unknown>) =>
  api.post<Post>(`/posts/${postId}/review`, action).then((r) => r.data);

export const schedulePost = (postId: number, scheduledAt: string) =>
  api.post<Post>(`/posts/${postId}/schedule`, null, { params: { scheduled_at: scheduledAt } }).then((r) => r.data);

export const publishNow = (postId: number) =>
  api.post(`/posts/${postId}/publish-now`).then((r) => r.data);

export const deletePost = (postId: number) =>
  api.delete(`/posts/${postId}`).then((r) => r.data);

export const fetchSummary = () =>
  api.get<Summary>("/analytics/summary").then((r) => r.data);

export const fetchTopPosts = (limit = 10) =>
  api.get("/analytics/top", { params: { limit } }).then((r) => r.data);

export const triggerDemoWorkflow = () =>
  api.get("/workflow/demo", { baseURL: `${BASE}/api/v1` }).then((r) => r.data);
