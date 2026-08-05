export default function RunsLoading() {
	return (
		<div className="mx-auto max-w-7xl" aria-live="polite">
			<div className="h-28 animate-pulse rounded-lg border border-slate-800 bg-slate-950" />
			<div className="mt-8 h-72 animate-pulse rounded-lg border border-slate-800 bg-slate-950" />
			<p className="sr-only">Loading eval runs…</p>
		</div>
	);
}
