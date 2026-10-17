"use client";

import { useState } from "react";

import {
  type AffectedCustomers,
  type AffectedSummary,
  fetchAffectedCustomers,
  UnauthorizedError,
} from "@/lib/api";

type Props = { summary: AffectedSummary; token: string; onUnauthorized: () => void };

function formatTime(value: string): string {
  const [date, time] = value.split("T");
  const [year, month, day] = date.split("-");
  return `${day}.${month}.${year} ${time}`;
}

/** L2 için etkilenen müşteri listesi. Veri doğrudan backend'den gelir; modelden geçmez. */
export function AffectedCustomersPanel({ summary, token, onUnauthorized }: Props) {
  const [data, setData] = useState<AffectedCustomers | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (data) return;
    setLoading(true);
    setError(null);
    try {
      setData(await fetchAffectedCustomers(summary, token));
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Liste alınamadı.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-3 border-t border-black/10 pt-3 dark:border-white/15">
      <button
        type="button"
        onClick={() => void toggle()}
        aria-expanded={open}
        className="rounded-lg border border-violet-600 px-3 py-1 text-sm font-medium text-violet-700 hover:bg-violet-50 dark:text-violet-300 dark:hover:bg-violet-950"
      >
        {open ? "Listeyi gizle" : `Etkilenen müşteriler (${summary.customer_count})`}
      </button>

      {open && (
        <div className="mt-3 space-y-2 text-sm">
          {loading && <p className="opacity-60">Liste getiriliyor…</p>}
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-red-700">
              {error}
            </p>
          )}
          {data && (
            <>
              <p>
                <strong>{data.total_customers}</strong> müşteri ·{" "}
                <strong>{data.callable_customers}</strong> müşteri telefonla aranabilir (iletişim
                izni var).
                {data.truncated && ` İlk ${data.rows.length} müşteri gösteriliyor.`}
              </p>
              <div className="max-h-80 overflow-auto rounded-lg border border-black/10 dark:border-white/15">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-white dark:bg-neutral-900">
                    <tr>
                      <th className="px-2 py-1">Müşteri no</th>
                      <th className="px-2 py-1">Ad soyad</th>
                      <th className="px-2 py-1">Telefon</th>
                      <th className="px-2 py-1">İletişim</th>
                      <th className="px-2 py-1">Son hata</th>
                      <th className="px-2 py-1">Kurum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row) => (
                      <tr key={row.customer_number} className="border-t border-black/5 dark:border-white/10">
                        <td className="px-2 py-1 font-mono">{row.customer_number}</td>
                        <td className="px-2 py-1">{row.full_name ?? "—"}</td>
                        <td className="px-2 py-1 font-mono whitespace-nowrap">{row.phone ?? "—"}</td>
                        <td className="px-2 py-1">
                          <span
                            className={
                              row.can_call
                                ? "whitespace-nowrap rounded bg-green-100 px-1.5 text-green-800"
                                : "whitespace-nowrap rounded bg-amber-100 px-1.5 text-amber-800"
                            }
                          >
                            {row.can_call ? "Aranabilir" : `Aranamaz · ${row.channel}`}
                          </span>
                        </td>
                        <td className="px-2 py-1 whitespace-nowrap">{formatTime(row.last_error_time)}</td>
                        <td className="px-2 py-1">{row.institution_code ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs opacity-60">
                Bu liste yapay zekâ modeline gönderilmez; görüntüleme kayıt altına alınır. Telefon
                izni olmayan müşterinin numarası maskelenir ve izinli kanal önerilir.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
