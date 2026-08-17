import type { NextConfig } from "next";

const backendApiBaseUrl = (
	process.env.BACKEND_API_BASE_URL ??
	process.env.NEXT_PUBLIC_API_BASE_URL ??
	"http://localhost:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
	productionBrowserSourceMaps: false,
	async rewrites() {
		return [
			{
				source: "/api/backend/:path*",
				destination: `${backendApiBaseUrl}/:path*`,
			},
		];
	},
	async headers() {
		return [
			{
				source: "/(.*)",
				headers: [
					{ key: "X-Content-Type-Options", value: "nosniff" },
					{ key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
					{ key: "X-Frame-Options", value: "DENY" },
					{
						key: "Permissions-Policy",
						value: "camera=(), microphone=(), geolocation=()",
					},
				],
			},
		];
	},
};

export default nextConfig;
