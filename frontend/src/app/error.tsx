"use client";

export default function DashboardError({ reset }: { reset: () => void }) {
	return (
		<div
			className="mx-auto max-w-3xl rounded-lg border border-rose-950 bg-rose-950/20 p-8"
			role="alert"
		>
			<h1 className="text-lg font-semibold text-rose-200">
				Unable to load dashboard
			</h1>
			<p className="mt-2 text-sm text-rose-200/70">
				Check that the backend is running and reachable, then try again.
			</p>
			<button
				className="mt-5 rounded-md border border-rose-800 px-3 py-2 text-sm font-medium text-rose-200 transition hover:bg-rose-900/40"
				onClick={reset}
				type="button"
			>
				Try again
			</button>
		</div>
	);
}
