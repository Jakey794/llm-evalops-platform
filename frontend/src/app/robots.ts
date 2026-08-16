import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
	return {
		rules: [
			{ userAgent: "*", allow: "/" },
			{ userAgent: ["GPTBot", "ChatGPT-User", "Google-Extended"], allow: "/" },
		],
		sitemap: `${siteConfig.url}/sitemap.xml`,
	};
}
