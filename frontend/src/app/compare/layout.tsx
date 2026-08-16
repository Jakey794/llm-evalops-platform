import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Compare evaluations",
	description: "Compare LLM evaluation runs across quality, cost, and latency.",
	alternates: { canonical: "/compare" },
	robots: { index: false, follow: false },
};

export default function CompareLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return children;
}
