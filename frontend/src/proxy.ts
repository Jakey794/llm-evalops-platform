import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/session";

const PUBLIC_PATHS = new Set([
	"/login",
	"/robots.txt",
	"/sitemap.xml",
	"/llms.txt",
	"/opengraph-image",
	"/manifest.webmanifest",
]);

export async function proxy(request: NextRequest): Promise<NextResponse> {
	const pathname = request.nextUrl.pathname;
	if (PUBLIC_PATHS.has(pathname) || pathname.startsWith("/api/auth/")) {
		if (pathname === "/login") {
			const session = await verifySession(
				request.cookies.get(SESSION_COOKIE)?.value,
			);
			if (session) return NextResponse.redirect(new URL("/", request.url));
		}
		return NextResponse.next();
	}

	const session = await verifySession(
		request.cookies.get(SESSION_COOKIE)?.value,
	);
	if (session) return NextResponse.next();
	if (pathname.startsWith("/api/")) {
		return NextResponse.json(
			{ detail: "Authentication required" },
			{ status: 401 },
		);
	}
	return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
	matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
