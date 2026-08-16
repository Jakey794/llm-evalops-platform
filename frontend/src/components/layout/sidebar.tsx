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
		<aside className="border-b border-slate-800 bg-slate-950 px-4 py-4 md:min-h-screen md:w-64 md:border-r md:border-b-0 md:px-5 md:py-6">
			<div>
				<p className="text-xs font-semibold uppercase text-slate-500">
					EvalOps / LLM Reliability
				</p>
				<p className="mt-2 text-xl font-semibold text-slate-50">
					Reliability Console
				</p>
				<p className="mt-1 text-sm text-slate-500">
					Prompt, model, dataset, and grader regression testing.
				</p>
			</div>

			<nav
				aria-label="Primary"
				className="mt-4 flex gap-1 overflow-x-auto md:mt-8 md:block md:space-y-1"
			>
				{navItems.map((item) => (
					<Link
						className="block shrink-0 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-900 hover:text-white"
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
