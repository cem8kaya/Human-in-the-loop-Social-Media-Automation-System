import clsx from "clsx";

const STATUS_STYLES: Record<string, string> = {
  generated: "bg-slate-100 text-slate-700",
  pending_review: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  scheduled: "bg-purple-100 text-purple-800",
  posted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"
      )}
    >
      {status.replace("_", " ")}
    </span>
  );
}
