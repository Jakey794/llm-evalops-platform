import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Datasets",
	description: "Browse evaluation datasets and their test cases.",
	alternates: { canonical: "/datasets" },
	robots: { index: false, follow: false },
};

export default function DatasetsLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return children;
}
