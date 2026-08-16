"use client";

import Link from "next/link";

export default function RunDetailError({ reset }: { reset: () => void }) {
	return (
		<div
			className="mx-auto max-w-3xl rounded-lg border border-rose-950 bg-rose-950/20 p-8"
			role="alert"
		>
			<h1 className="text-lg font-semibold text-rose-200">
				Unable to load this eval run
			</h1>
			<p className="mt-2 text-sm text-rose-200/70">
				The run may not exist, or the backend may be unavailable.
			</p>
			<div className="mt-5 flex gap-3">
				<button
					className="rounded-md border border-rose-800 px-3 py-2 text-sm font-medium text-rose-200 transition hover:bg-rose-900/40"
					onClick={reset}
					type="button"
				>
					Try again
				</button>
				<Link
					className="rounded-md border border-slate-700 px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-900"
					href="/runs"
				>
					Back to runs
				</Link>
			</div>
		</div>
	);
}
