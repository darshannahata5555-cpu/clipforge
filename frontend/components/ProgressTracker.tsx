"use client";

const STEPS = [
  { key: "transcribing", label: "Transcribing" },
  { key: "generating",   label: "Writing posts" },
  { key: "cutting",      label: "Creating shorts" },
  { key: "complete",     label: "Done" },
];

interface Props {
  progress: number;
  stepLabel: string;
  status: string;
}

export default function ProgressTracker({ progress, stepLabel, status }: Props) {
  const currentIdx = STEPS.findIndex((s) => s.key === status);

  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 mb-8">
      {/* Step indicators */}
      <div className="flex items-center gap-0 mb-6">
        {STEPS.map((step, i) => {
          const done = i < currentIdx || status === "complete";
          const active = i === currentIdx;
          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    done
                      ? "bg-indigo-500 text-white"
                      : active
                      ? "bg-indigo-500/30 text-indigo-400 ring-2 ring-indigo-500"
                      : "bg-[var(--border)] text-zinc-600"
                  }`}
                >
                  {done ? "✓" : i + 1}
                </div>
                <span
                  className={`text-xs mt-1.5 whitespace-nowrap ${
                    active ? "text-indigo-400" : done ? "text-zinc-400" : "text-zinc-600"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 mb-5 transition-colors ${
                    i < currentIdx ? "bg-indigo-500" : "bg-[var(--border)]"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-[var(--border)] rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-zinc-400 text-sm mt-3">{stepLabel}</p>
    </div>
  );
}
