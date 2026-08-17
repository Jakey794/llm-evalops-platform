import { NextResponse } from "next/server";
import {
	checkLoginRateLimit,
	clearLoginRateLimit,
} from "@/lib/login-rate-limit";
import { hasSameOrigin } from "@/lib/request-origin";
import {
	constantTimeEqual,
	createSession,
	SESSION_COOKIE,
	SESSION_MAX_AGE_SECONDS,
	type SessionRole,
} from "@/lib/session";

export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
	if (!hasSameOrigin(request)) {
		return NextResponse.json(
			{ detail: "Invalid request origin" },
			{ status: 403 },
		);
	}
	const clientKey = getClientKey(request);
	const rateLimit = checkLoginRateLimit(clientKey);
	if (!rateLimit.allowed) {
		audit("login.rate_limited", { client: clientKey });
		return NextResponse.json(
			{ detail: "Too many login attempts. Try again later." },
			{ status: 429, headers: { "Retry-After": String(rateLimit.retryAfter) } },
		);
	}

	let password = "";
	try {
		const body = (await request.json()) as { password?: unknown };
		if (typeof body.password === "string" && body.password.length <= 256) {
			password = body.password;
		}
	} catch {
		return NextResponse.json({ detail: "Invalid request" }, { status: 400 });
	}

	const operatorPassword = process.env.APP_OPERATOR_PASSWORD;
	const viewerPassword = process.env.APP_VIEWER_PASSWORD;
	if (
		!process.env.APP_SESSION_SECRET ||
		process.env.APP_SESSION_SECRET.length < 32 ||
		!operatorPassword ||
		operatorPassword.length < 16 ||
		!viewerPassword ||
		viewerPassword.length < 16 ||
		operatorPassword === viewerPassword
	) {
		audit("login.configuration_error", { client: clientKey });
		return NextResponse.json(
			{ detail: "Authentication is not configured" },
			{ status: 503 },
		);
	}

	let role: SessionRole | null = null;
	if (await constantTimeEqual(password, operatorPassword)) role = "operator";
	else if (await constantTimeEqual(password, viewerPassword)) role = "viewer";
	if (!role) {
		audit("login.denied", { client: clientKey });
		return NextResponse.json(
			{ detail: "Invalid credentials" },
			{ status: 401 },
		);
	}

	clearLoginRateLimit(clientKey);
	const session = await createSession(role);
	const response = NextResponse.json({ ok: true, role });
	response.cookies.set(SESSION_COOKIE, session, {
		httpOnly: true,
		secure: process.env.NODE_ENV === "production",
		sameSite: "strict",
		path: "/",
		maxAge: SESSION_MAX_AGE_SECONDS,
		priority: "high",
	});
	response.headers.set("Cache-Control", "no-store");
	audit("login.succeeded", { client: clientKey, role });
	return response;
}

function getClientKey(request: Request): string {
	return (
		request.headers.get("x-vercel-forwarded-for")?.split(",")[0]?.trim() ||
		request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
		"unknown"
	).slice(0, 128);
}

function audit(event: string, fields: Record<string, unknown>): void {
	console.info(JSON.stringify({ event, ...fields }));
}
