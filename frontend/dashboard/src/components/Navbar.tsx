"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/trends", label: "Trends" },
  { href: "/review", label: "Review Queue" },
  { href: "/scheduled", label: "Scheduled" },
  { href: "/analytics", label: "Analytics" },
];

export default function Navbar() {
  const path = usePathname();
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-6 h-14">
        <span className="font-bold text-blue-600 text-lg shrink-0">SocialBot</span>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={clsx(
              "text-sm font-medium transition-colors",
              path === l.href
                ? "text-blue-600 border-b-2 border-blue-600 pb-0.5"
                : "text-slate-600 hover:text-blue-600"
            )}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
