import type { MetricCardProps } from "@/lib/types";

export function MetricCard({ label, value, helperText }: MetricCardProps) {
	return (
		<div className="rounded-lg border border-slate-800 bg-slate-950 p-5 shadow-sm shadow-black/20">
			<p className="text-sm font-medium text-slate-400">{label}</p>
			<p className="mt-3 text-3xl font-semibold tracking-tight text-slate-50">
				{value}
			</p>
			<p className="mt-2 text-sm text-slate-500">{helperText}</p>
		</div>
	);
}
