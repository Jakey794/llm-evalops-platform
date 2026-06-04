import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import "./globals.css";

export const metadata: Metadata = {
	title: "LLM Reliability + EvalOps Platform",
	description:
		"Evaluate LLM apps across prompts, models, datasets, and graders.",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en">
			<body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
				<div className="flex min-h-screen">
					<Sidebar />
					<main className="flex-1 px-6 py-6 md:px-10">{children}</main>
				</div>
			</body>
		</html>
	);
}
