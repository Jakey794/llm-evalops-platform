import Link from "next/link";

const navItems = [
	{ href: "/", label: "Dashboard" },
	{ href: "/datasets", label: "Datasets" },
	{ href: "/prompts", label: "Prompts" },
	{ href: "/runs", label: "Runs" },
	{ href: "/runs/new", label: "New evaluation" },
	{ href: "/compare", label: "Compare" },
];

export function Sidebar() {
	return (
		<aside className="hidden min-h-screen w-64 border-r border-slate-800 bg-slate-950 px-5 py-6 md:block">
			<div>
				<p className="text-xs font-semibold uppercase text-slate-500">
					EvalOps / LLM Reliability
				</p>
				<h1 className="mt-2 text-xl font-semibold text-slate-50">
					Reliability Console
				</h1>
				<p className="mt-2 text-sm text-slate-500">
					Prompt, model, dataset, and grader regression testing.
				</p>
			</div>

			<nav className="mt-8 space-y-1">
				{navItems.map((item) => (
					<Link
						className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-900 hover:text-white"
						href={item.href}
						key={item.href}
					>
						{item.label}
					</Link>
				))}
			</nav>
		</aside>
	);
}
