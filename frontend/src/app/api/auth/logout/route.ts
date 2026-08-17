import { NextResponse } from "next/server";
import { getExternalOrigin, hasSameOrigin } from "@/lib/request-origin";
import { SESSION_COOKIE } from "@/lib/session";

export async function POST(request: Request): Promise<Response> {
	if (request.headers.get("origin") && !hasSameOrigin(request)) {
		return NextResponse.json(
			{ detail: "Invalid request origin" },
			{ status: 403 },
		);
	}
	const response = NextResponse.redirect(
		new URL("/login", getExternalOrigin(request)),
		303,
	);
	response.cookies.set(SESSION_COOKIE, "", {
		httpOnly: true,
		secure: process.env.NODE_ENV === "production",
		sameSite: "strict",
		path: "/",
		maxAge: 0,
	});
	response.headers.set("Cache-Control", "no-store");
	console.info(JSON.stringify({ event: "logout.succeeded" }));
	return response;
}
