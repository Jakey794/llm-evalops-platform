import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { siteConfig } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
	metadataBase: new URL(siteConfig.url),
	title: { default: siteConfig.name, template: `%s | ${siteConfig.shortName}` },
	description: siteConfig.description,
	applicationName: siteConfig.shortName,
	keywords: ["LLM evaluation", "EvalOps", "AI reliability", "MLOps"],
	alternates: { canonical: "/" },
	openGraph: {
		type: "website",
		url: "/",
		title: siteConfig.name,
		description: siteConfig.description,
		siteName: siteConfig.shortName,
	},
	twitter: {
		card: "summary_large_image",
		title: siteConfig.name,
		description: siteConfig.description,
	},
	robots: {
		index: true,
		follow: true,
		googleBot: {
			index: true,
			follow: true,
			"max-image-preview": "large",
			"max-snippet": -1,
		},
	},
};

const structuredData = JSON.stringify({
	"@context": "https://schema.org",
	"@type": "WebApplication",
	name: siteConfig.name,
	description: siteConfig.description,
	url: siteConfig.url,
	applicationCategory: "DeveloperApplication",
	operatingSystem: "Web",
});

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en">
			<body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
				<script type="application/ld+json">{structuredData}</script>
				<div className="flex min-h-screen flex-col md:flex-row">
					<Sidebar />
					<main className="flex-1 px-6 py-6 md:px-10">{children}</main>
				</div>
			</body>
		</html>
	);
}
