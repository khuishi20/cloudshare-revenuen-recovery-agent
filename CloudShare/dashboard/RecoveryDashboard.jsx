import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { AlertTriangle, ArrowUpRight, CircleSlash, MessageCircle, RotateCcw } from "lucide-react";

// ---- Design tokens (ledger / receipt aesthetic) ----
// bg: deep ink navy, text: warm off-white, accent: marigold for recovered
// money, muted rose for at-risk/failed. Numbers set in monospace like a
// real settlement ledger; everything else in a plain humanist sans.
const T = {
  bg: "#0E1420",
  surface: "#161D2E",
  surfaceRaised: "#1B2338",
  border: "#232B3D",
  text: "#F2EFE9",
  muted: "#8B93A7",
  amber: "#E7A94C",
  rose: "#C9707A",
};

const API_BASE = "/api/v1/recovery"; // adjust if your Spring Boot context path differs

const CAUSE_LABEL = {
  INSUFFICIENT_FUNDS: "Insufficient funds",
  CARD_EXPIRED: "Card expired",
  BANK_TIMEOUT: "Bank timeout",
  USER_ABANDONED: "Checkout abandoned",
  SIGNATURE_MISMATCH: "Signature mismatch",
  OTP_FAILED: "OTP failed",
  UNKNOWN: "Unknown",
};

const OUTCOME_META = {
  RETRY_INITIATED: { label: "Retry sent", icon: RotateCcw, color: T.amber },
  MESSAGE_QUEUED: { label: "Reminder queued", icon: MessageCircle, color: "#7CA9C9" },
  ESCALATED: { label: "Escalated", icon: AlertTriangle, color: T.rose },
  EXHAUSTED: { label: "Exhausted", icon: CircleSlash, color: T.muted },
};

// Demo data so the dashboard renders something meaningful even before the
// backend is wired up - swap for real fetch results automatically once
// /recovery/metrics and /recovery/audit respond.
const DEMO_METRICS = {
  totalFailedTransactions: 45,
  retryAttemptsCreated: 27,
  attemptedAmount: 24865,
  recoveredAmount: 9430,
  recoveryRatePct: 37.9,
  byDiagnosedCause: {
    INSUFFICIENT_FUNDS: 13,
    CARD_EXPIRED: 6,
    BANK_TIMEOUT: 9,
    USER_ABANDONED: 13,
    OTP_FAILED: 2,
    SIGNATURE_MISMATCH: 2,
  },
  byOutcome: { RETRY_INITIATED: 18, MESSAGE_QUEUED: 21, ESCALATED: 2, EXHAUSTED: 4 },
};

const DEMO_AUDIT = [
  { orderId: "order_seed_0031", diagnosedCause: "BANK_TIMEOUT", confidence: 0.8, recommendedAction: "RETRY", outcome: "RETRY_INITIATED", amount: 1499, attemptNumber: 1, decidedAt: "2026-08-20T14:02:00" },
  { orderId: "order_seed_0012", diagnosedCause: "USER_ABANDONED", confidence: 0.9, recommendedAction: "REMIND", outcome: "MESSAGE_QUEUED", amount: 499, attemptNumber: 1, decidedAt: "2026-08-20T14:01:40" },
  { orderId: "order_seed_0005", diagnosedCause: "SIGNATURE_MISMATCH", confidence: 0.99, recommendedAction: "ESCALATE", outcome: "ESCALATED", amount: 2999, attemptNumber: 1, decidedAt: "2026-08-20T14:01:10" },
  { orderId: "order_seed_0044", diagnosedCause: "INSUFFICIENT_FUNDS", confidence: 0.85, recommendedAction: "STOP", outcome: "EXHAUSTED", amount: 1499, attemptNumber: 3, decidedAt: "2026-08-20T14:00:55" },
];

function formatINR(n) {
  return `₹${Number(n).toLocaleString("en-IN")}`;
}

function StampBadge({ children, color }) {
  return (
    <span
      className="inline-block px-2 py-0.5 text-[10px] font-mono tracking-widest uppercase border-2 rounded"
      style={{ color, borderColor: color, transform: "rotate(-3deg)" }}
    >
      {children}
    </span>
  );
}

export default function RecoveryDashboard() {
  const [metrics, setMetrics] = useState(DEMO_METRICS);
  const [audit, setAudit] = useState(DEMO_AUDIT);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [mRes, aRes] = await Promise.all([
          fetch(`${API_BASE}/metrics`),
          fetch(`${API_BASE}/audit`),
        ]);
        if (!mRes.ok || !aRes.ok) throw new Error("API not ready");
        const m = await mRes.json();
        const a = await aRes.json();
        if (!cancelled) {
          setMetrics(m);
          setAudit(a);
          setIsLive(true);
        }
      } catch {
        // stay on demo data - backend probably isn't running yet
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const causeData = Object.entries(metrics.byDiagnosedCause || {}).map(([cause, count]) => ({
    cause: CAUSE_LABEL[cause] || cause,
    count,
  }));

  return (
    <div
      className="min-h-screen w-full font-sans"
      style={{ background: T.bg, color: T.text }}
    >
      <div className="max-w-5xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8 pb-6" style={{ borderBottom: `1px solid ${T.border}` }}>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-mono" style={{ color: T.muted }}>
              CloudShare · Revenue Recovery Ledger
            </p>
            <h1 className="text-2xl font-semibold mt-1">Recovery Agent</h1>
          </div>
          <span className="text-[11px] font-mono px-2 py-1 rounded" style={{ background: T.surfaceRaised, color: isLive ? T.amber : T.muted }}>
            {loading ? "connecting…" : isLive ? "● live" : "○ demo data"}
          </span>
        </div>

        {/* Hero metric */}
        <div
          className="rounded-lg p-6 mb-8 flex items-end justify-between"
          style={{ background: T.surface, border: `1px solid ${T.border}` }}
        >
          <div>
            <p className="text-xs uppercase tracking-widest font-mono mb-2" style={{ color: T.muted }}>
              Recovered vs attempted
            </p>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-mono font-semibold" style={{ color: T.amber }}>
                {formatINR(metrics.recoveredAmount)}
              </span>
              <span className="text-lg font-mono" style={{ color: T.muted }}>
                / {formatINR(metrics.attemptedAmount)}
              </span>
            </div>
            <div className="mt-3">
              <StampBadge color={T.amber}>{metrics.recoveryRatePct}% recovered</StampBadge>
            </div>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-xs font-mono" style={{ color: T.muted }}>
              {metrics.totalFailedTransactions} failures diagnosed
            </p>
            <p className="text-xs font-mono" style={{ color: T.muted }}>
              {metrics.retryAttemptsCreated} recovery actions taken
            </p>
          </div>
        </div>

        {/* Cause breakdown chart */}
        <div className="rounded-lg p-6 mb-8" style={{ background: T.surface, border: `1px solid ${T.border}` }}>
          <p className="text-xs uppercase tracking-widest font-mono mb-4" style={{ color: T.muted }}>
            Diagnosed failure causes
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={causeData} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={T.border} horizontal={false} />
              <XAxis type="number" tick={{ fill: T.muted, fontSize: 11 }} axisLine={{ stroke: T.border }} tickLine={false} />
              <YAxis
                type="category"
                dataKey="cause"
                width={140}
                tick={{ fill: T.text, fontSize: 12 }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: T.surfaceRaised, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text }}
                cursor={{ fill: T.surfaceRaised }}
              />
              <Bar dataKey="count" fill={T.amber} radius={[0, 3, 3, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Audit trail */}
        <div className="rounded-lg overflow-hidden" style={{ background: T.surface, border: `1px solid ${T.border}` }}>
          <p className="text-xs uppercase tracking-widest font-mono px-6 pt-6 pb-4" style={{ color: T.muted }}>
            Audit trail — every decision, explained
          </p>
          <div className="divide-y" style={{ borderColor: T.border }}>
            {audit.map((entry, i) => {
              const meta = OUTCOME_META[entry.outcome] || OUTCOME_META.EXHAUSTED;
              const Icon = meta.icon;
              return (
                <div key={entry.orderId + i} className="px-6 py-4 flex items-center gap-4" style={{ borderColor: T.border }}>
                  <Icon size={16} style={{ color: meta.color, flexShrink: 0 }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm truncate">{entry.orderId}</span>
                      <span className="text-xs" style={{ color: T.muted }}>
                        {CAUSE_LABEL[entry.diagnosedCause] || entry.diagnosedCause}
                      </span>
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: T.muted }}>
                      attempt #{entry.attemptNumber} · confidence {(entry.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <span className="font-mono text-sm" style={{ color: T.text }}>
                    {formatINR(entry.amount)}
                  </span>
                  <span
                    className="text-[10px] font-mono uppercase tracking-wider px-2 py-1 rounded flex items-center gap-1"
                    style={{ color: meta.color, background: T.surfaceRaised }}
                  >
                    <ArrowUpRight size={10} />
                    {meta.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
