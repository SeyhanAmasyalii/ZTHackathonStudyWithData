import type { ScenarioLink } from "@/lib/api";

/** Yalnızca https bağlantılar (backend de doğrular); yeni sekmede, sayfaya erişim vermeden açılır. */
function isSafe(url: string): boolean {
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false;
  }
}

export function ScenarioLinks({ links }: { links: ScenarioLink[] }) {
  const safe = links.filter((link) => isSafe(link.url));
  if (safe.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2 border-t border-black/10 pt-3 dark:border-white/10">
      {safe.map((link) => (
        <a
          key={link.solution_template_id}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-violet-600 px-3 py-1 text-sm text-violet-700 hover:bg-violet-50 dark:text-violet-300 dark:hover:bg-violet-950"
          title={link.title}
        >
          ▶ Akışı izle · {link.solution_template_id}
          {link.title ? ` — ${link.title}` : ""}
        </a>
      ))}
    </div>
  );
}
