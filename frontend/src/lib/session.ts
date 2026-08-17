export const SESSION_COOKIE = "evalops_session";
export const SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;

export type SessionRole = "viewer" | "operator";

export type Session = {
	subject: string;
	role: SessionRole;
	expiresAt: number;
};

type SessionPayload = {
	sub: string;
	role: SessionRole;
	exp: number;
};

const encoder = new TextEncoder();

export async function createSession(role: SessionRole): Promise<string> {
	const secret = getSessionSecret();
	if (!secret) throw new Error("APP_SESSION_SECRET is not configured");
	const payload: SessionPayload = {
		sub: role === "operator" ? "dashboard-operator" : "dashboard-viewer",
		role,
		exp: Math.floor(Date.now() / 1000) + SESSION_MAX_AGE_SECONDS,
	};
	const encodedPayload = encodeBase64Url(JSON.stringify(payload));
	const signature = await sign(encodedPayload, secret);
	return `${encodedPayload}.${signature}`;
}

export async function verifySession(
	value: string | undefined,
): Promise<Session | null> {
	const secret = getSessionSecret();
	if (!secret || !value) return null;
	const [encodedPayload, signature, extra] = value.split(".");
	if (!encodedPayload || !signature || extra) return null;
	if (!(await verify(encodedPayload, signature, secret))) return null;

	try {
		const parsed = JSON.parse(
			decodeBase64Url(encodedPayload),
		) as Partial<SessionPayload>;
		if (
			(parsed.role !== "viewer" && parsed.role !== "operator") ||
			typeof parsed.sub !== "string" ||
			typeof parsed.exp !== "number" ||
			parsed.exp <= Math.floor(Date.now() / 1000)
		) {
			return null;
		}
		return { subject: parsed.sub, role: parsed.role, expiresAt: parsed.exp };
	} catch {
		return null;
	}
}

export async function constantTimeEqual(
	left: string,
	right: string,
): Promise<boolean> {
	const [leftHash, rightHash] = await Promise.all([
		crypto.subtle.digest("SHA-256", encoder.encode(left)),
		crypto.subtle.digest("SHA-256", encoder.encode(right)),
	]);
	const leftBytes = new Uint8Array(leftHash);
	const rightBytes = new Uint8Array(rightHash);
	let difference = 0;
	for (let index = 0; index < leftBytes.length; index += 1) {
		difference |= leftBytes[index] ^ rightBytes[index];
	}
	return difference === 0;
}

function getSessionSecret(): string | null {
	const secret = process.env.APP_SESSION_SECRET;
	return secret && secret.length >= 32 ? secret : null;
}

async function sign(payload: string, secret: string): Promise<string> {
	const key = await crypto.subtle.importKey(
		"raw",
		encoder.encode(secret),
		{ name: "HMAC", hash: "SHA-256" },
		false,
		["sign"],
	);
	const signature = await crypto.subtle.sign(
		"HMAC",
		key,
		encoder.encode(payload),
	);
	return bytesToBase64Url(new Uint8Array(signature));
}

async function verify(
	payload: string,
	signature: string,
	secret: string,
): Promise<boolean> {
	try {
		const key = await crypto.subtle.importKey(
			"raw",
			encoder.encode(secret),
			{ name: "HMAC", hash: "SHA-256" },
			false,
			["verify"],
		);
		return crypto.subtle.verify(
			"HMAC",
			key,
			base64UrlToBytes(signature).buffer as ArrayBuffer,
			encoder.encode(payload),
		);
	} catch {
		return false;
	}
}

function encodeBase64Url(value: string): string {
	return bytesToBase64Url(encoder.encode(value));
}

function decodeBase64Url(value: string): string {
	return new TextDecoder().decode(base64UrlToBytes(value));
}

function bytesToBase64Url(bytes: Uint8Array): string {
	let binary = "";
	for (const byte of bytes) binary += String.fromCharCode(byte);
	return btoa(binary)
		.replaceAll("+", "-")
		.replaceAll("/", "_")
		.replace(/=+$/, "");
}

function base64UrlToBytes(value: string): Uint8Array {
	const padded = value
		.replaceAll("-", "+")
		.replaceAll("_", "/")
		.padEnd(Math.ceil(value.length / 4) * 4, "=");
	const binary = atob(padded);
	return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}
