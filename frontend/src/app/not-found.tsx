import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
	title: "Page not found",
	description: "The requested LLM EvalOps page could not be found.",
	robots: { index: false, follow: false },
};

export default function NotFound() {
	return (
		<div className="mx-auto max-w-2xl py-16">
			<p className="text-sm font-medium uppercase tracking-wide text-slate-500">
				404
			</p>
			<h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
				Page not found
			</h1>
			<p className="mt-3 text-sm leading-6 text-slate-400">
				The page you requested does not exist or may have moved.
			</p>
			<Link
				className="mt-6 inline-flex rounded-md border border-cyan-800 bg-cyan-950/40 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-900/40"
				href="/"
			>
				Return to the dashboard
			</Link>
		</div>
	);
}
