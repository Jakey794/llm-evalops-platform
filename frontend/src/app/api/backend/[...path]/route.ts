import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { hasSameOrigin } from "@/lib/request-origin";
import { SESSION_COOKIE, verifySession } from "@/lib/session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_PREFIXES = [
	"datasets",
	"eval-runs",
	"prompt-versions",
	"model-configs",
];
const MAX_BODY_BYTES = 2 * 1024 * 1024;

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(
	request: NextRequest,
	context: RouteContext,
): Promise<Response> {
	const session = await verifySession(
		request.cookies.get(SESSION_COOKIE)?.value,
	);
	if (!session)
		return NextResponse.json(
			{ detail: "Authentication required" },
			{ status: 401 },
		);
	if (request.method !== "GET" && session.role !== "operator") {
		audit(request, "gateway.authorization_denied", session.subject, 403);
		return NextResponse.json(
			{ detail: "Operator role required" },
			{ status: 403 },
		);
	}
	if (request.method !== "GET" && !hasSameOrigin(request)) {
		return NextResponse.json(
			{ detail: "Invalid request origin" },
			{ status: 403 },
		);
	}

	const { path: segments } = await context.params;
	if (!isAllowedPath(segments)) {
		return NextResponse.json(
			{ detail: "Backend path is not allowed" },
			{ status: 404 },
		);
	}
	const configuredLength = Number(request.headers.get("content-length") ?? "0");
	if (configuredLength > MAX_BODY_BYTES) {
		return NextResponse.json(
			{ detail: "Request body is too large" },
			{ status: 413 },
		);
	}

	const baseUrl = (
		process.env.BACKEND_API_BASE_URL ??
		process.env.NEXT_PUBLIC_API_BASE_URL ??
		""
	).replace(/\/$/, "");
	const token =
		session.role === "operator"
			? process.env.BACKEND_OPERATOR_TOKEN
			: process.env.BACKEND_VIEWER_TOKEN;
	if (!isSecureBackendConfiguration(baseUrl, token)) {
		audit(request, "gateway.configuration_error", session.subject, 503);
		return NextResponse.json(
			{ detail: "Backend gateway is not configured" },
			{ status: 503 },
		);
	}

	const body =
		request.method === "GET" ? undefined : await request.arrayBuffer();
	if (body && body.byteLength > MAX_BODY_BYTES) {
		return NextResponse.json(
			{ detail: "Request body is too large" },
			{ status: 413 },
		);
	}
	const requestId = crypto.randomUUID();
	const headers = new Headers({
		Accept: "application/json",
		Authorization: `Bearer ${token}`,
		"X-Request-ID": requestId,
	});
	const contentType = request.headers.get("content-type");
	if (contentType) headers.set("Content-Type", contentType);

	try {
		const upstream = await fetch(
			`${baseUrl}/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
			{
				method: request.method,
				headers,
				body,
				cache: "no-store",
				redirect: "manual",
			},
		);
		const responseHeaders = new Headers({
			"Cache-Control": "no-store",
			"X-Request-ID": upstream.headers.get("x-request-id") ?? requestId,
		});
		const responseType = upstream.headers.get("content-type");
		if (responseType) responseHeaders.set("Content-Type", responseType);
		const retryAfter = upstream.headers.get("retry-after");
		if (retryAfter) responseHeaders.set("Retry-After", retryAfter);
		audit(
			request,
			"gateway.request",
			session.subject,
			upstream.status,
			requestId,
		);
		return new Response(upstream.body, {
			status: upstream.status,
			headers: responseHeaders,
		});
	} catch {
		audit(
			request,
			"gateway.upstream_unavailable",
			session.subject,
			502,
			requestId,
		);
		return NextResponse.json(
			{ detail: "Backend is unavailable" },
			{ status: 502 },
		);
	}
}

function isSecureBackendConfiguration(
	baseUrl: string,
	token: string | undefined,
): token is string {
	if (!token || token.length < 32) return false;
	try {
		const url = new URL(baseUrl);
		return (
			url.protocol === "https:" ||
			(url.protocol === "http:" &&
				["localhost", "127.0.0.1"].includes(url.hostname))
		);
	} catch {
		return false;
	}
}

function isAllowedPath(segments: string[]): boolean {
	return (
		segments.length > 0 &&
		ALLOWED_PREFIXES.includes(segments[0]) &&
		segments.every(
			(segment) => /^[A-Za-z0-9._~-]+$/.test(segment) && segment !== "..",
		)
	);
}

function audit(
	request: NextRequest,
	event: string,
	subject: string,
	status: number,
	requestId?: string,
): void {
	console.info(
		JSON.stringify({
			event,
			requestId,
			method: request.method,
			path: request.nextUrl.pathname,
			status,
			subject,
		}),
	);
}

export const GET = forward;
export const POST = forward;
