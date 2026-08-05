export default function RunDetailLoading() {
	return (
		<div className="mx-auto max-w-7xl" aria-live="polite">
			<div className="h-32 animate-pulse rounded-lg border border-slate-800 bg-slate-950" />
			<div className="mt-8 h-56 animate-pulse rounded-lg border border-slate-800 bg-slate-950" />
			<div className="mt-8 h-72 animate-pulse rounded-lg border border-slate-800 bg-slate-950" />
			<p className="sr-only">Loading eval run detail…</p>
		</div>
	);
}
