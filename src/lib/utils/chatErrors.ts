// CHOn (T17): turn raw chat errors into a specific cause and next step
// (WG-AI-PLA-00002, section 8 / PP-05: "Every error names the cause and the next step").
//
// The backend sends errors as { content, status?, code?, finish_reason? }.
// `content` is usually the provider's text, sometimes a provider error object.

export type ChatErrorKind =
	| 'empty'
	| 'stopped'
	| 'content_filter'
	| 'rate_limit'
	| 'context_length'
	| 'auth'
	| 'connector'
	| 'model_unavailable'
	| 'network'
	| 'file'
	| 'unknown';

export type ChatErrorInput = {
	content?: unknown;
	status?: number;
	code?: string;
	finish_reason?: string;
};

export type ExplainedError = {
	kind: ChatErrorKind;
	title: string;
	nextStep: string;
	details: string;
	canRetry: boolean;
	/** Neutral notice (e.g. user stopped the answer) rather than a failure. */
	neutral?: boolean;
};

type T = (key: string, options?: Record<string, unknown>) => string;

/** Readable text from a string or a provider error object. */
export const errorText = (value: unknown): string => {
	if (typeof value === 'string') return value;
	if (value && typeof value === 'object') {
		const v = value as Record<string, unknown>;
		const inner = v.error;
		if (inner && typeof inner === 'object' && typeof (inner as any).message === 'string') {
			return (inner as any).message;
		}
		if (typeof inner === 'string') return inner;
		if (typeof v.detail === 'string') return v.detail;
		if (typeof v.message === 'string') return v.message;
		try {
			return JSON.stringify(value);
		} catch {
			return String(value);
		}
	}
	return value == null ? '' : String(value);
};

const findCode = (value: unknown, depth = 0): string => {
	if (!value || typeof value !== 'object' || depth > 4) return '';
	const v = value as Record<string, unknown>;
	for (const key of ['innererror', 'inner_error', 'error']) {
		const nested = findCode(v[key], depth + 1);
		if (nested) return nested;
	}
	for (const key of ['code', 'type']) {
		if (typeof v[key] === 'string' && v[key]) return v[key] as string;
	}
	return '';
};

const has = (haystack: string, ...needles: (string | RegExp)[]) =>
	needles.some((n) => (typeof n === 'string' ? haystack.includes(n) : n.test(haystack)));

/** Classify an error. Pure function so it can be unit tested. */
export const classifyChatError = (error: ChatErrorInput | null | undefined): ChatErrorKind => {
	if (!error) return 'unknown';
	const status = typeof error.status === 'number' ? error.status : undefined;
	const code = (error.code || findCode(error.content) || '').toLowerCase();
	const text = errorText(error.content).toLowerCase();
	const all = `${code} ${text} ${error.finish_reason ?? ''}`.toLowerCase();

	if (code === 'empty_response') {
		if (error.finish_reason === 'content_filter') return 'content_filter';
		return 'empty';
	}
	if (
		has(all, 'content_filter', 'responsibleaipolicyviolation', 'content management policy', 'safety filter', 'jailbreak')
	)
		return 'content_filter';
	if (
		status === 429 ||
		has(all, 'rate_limit', 'rate limit', 'too many requests', 'quota', 'token budget', 'budget exceeded', 'limit reached', 'insufficient_quota')
	)
		return 'rate_limit';
	if (
		has(all, 'context_length', 'context length', 'maximum context', 'too many tokens', 'prompt is too long', 'input is too long', 'reduce the length', 'token limit')
	)
		return 'context_length';
	if (
		has(all, 'mcp server', 'tool server', 'failed to connect to mcp', 'oauth', 'invalid_grant', 'aadsts') &&
		!has(all, 'model')
	)
		return has(all, 'invalid_grant', 'aadsts', 'expired', 'sign in', 'unauthor', '401') ? 'auth' : 'connector';
	if (status === 401 || status === 403 || has(all, 'unauthorized', 'not authenticated', 'session expired', 'token expired', 'invalid api key', 'incorrect api key'))
		return 'auth';
	if (status === 404 || has(all, 'model not found', 'model_not_found', 'deploymentnotfound', 'does not exist', 'no such model'))
		return 'model_unavailable';
	if (status === 413 || has(all, 'file too large', 'payload too large', 'unsupported file', 'could not read file'))
		return 'file';
	if (
		(status !== undefined && status >= 500) ||
		has(all, 'failed to fetch', 'networkerror', 'network error', 'timeout', 'timed out', 'econnreset', 'econnrefused', 'server connection', 'connection error', 'service unavailable', 'bad gateway', 'overloaded', /\b50[234]\b/)
	)
		return 'network';
	return 'unknown';
};

/** Cause, next step and details for the error card. */
export const explainChatError = (
	t: T,
	error: ChatErrorInput | null | undefined,
	opts: { stopped?: boolean } = {}
): ExplainedError => {
	if (opts.stopped) {
		return {
			kind: 'stopped',
			title: t('You stopped this answer.'),
			nextStep: t('It may be incomplete. Select Retry to get a full answer.'),
			details: '',
			canRetry: true,
			neutral: true
		};
	}

	const kind = classifyChatError(error);
	const raw = errorText(error?.content).trim();
	const meta = [
		error?.status ? `HTTP ${error.status}` : '',
		error?.code ? `code: ${error.code}` : '',
		error?.finish_reason ? `finish_reason: ${error.finish_reason}` : ''
	]
		.filter(Boolean)
		.join(' · ');
	const details = [raw, meta].filter(Boolean).join('\n');

	const explained: Record<ChatErrorKind, [string, string, boolean]> = {
		empty: [
			raw && error?.code === 'empty_response' ? t(raw) : t('CHOn did not return an answer.'),
			t('Try again. If it keeps happening, rephrase the question or report it.'),
			true
		],
		stopped: ['', '', true],
		content_filter: [
			t('The AI service blocked this request with its safety filter.'),
			t('Rephrase your message without the flagged wording and try again.'),
			true
		],
		rate_limit: [
			t('You have reached the usage limit for now.'),
			t('Wait a few minutes, then try again.'),
			true
		],
		context_length: [
			t('This chat is too long for the selected model.'),
			t('Start a new chat, or remove large files from this one, and try again.'),
			false
		],
		auth: [
			t('Your sign-in for a connected service has expired.'),
			t('Sign in again (refresh the page or reconnect the service), then try again.'),
			true
		],
		connector: [
			t('A connected service (Outlook, SharePoint or another tool) did not respond.'),
			t('Try again in a moment. If it keeps failing, the service may be down.'),
			true
		],
		model_unavailable: [
			t('The selected model is not available right now.'),
			t('Choose another model in the model selector and try again.'),
			false
		],
		network: [
			t('CHOn could not reach the AI service.'),
			t('Check your connection, wait a moment and try again.'),
			true
		],
		file: [
			t('CHOn could not use one of the attached files.'),
			t('Check the file type and size, attach it again and retry.'),
			true
		],
		unknown: [
			t('Something went wrong while CHOn was answering.'),
			t('Try again. If it keeps happening, report it so the CHOn team can look at it.'),
			true
		]
	};

	const [title, nextStep, canRetry] = explained[kind];
	return { kind, title, nextStep, details, canRetry };
};
