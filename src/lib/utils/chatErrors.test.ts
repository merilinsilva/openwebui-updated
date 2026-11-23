import { describe, expect, it } from 'vitest';
import { classifyChatError, explainChatError, errorText } from './chatErrors';

const t = (key: string) => key;

describe('classifyChatError (CHOn T17)', () => {
	it.each([
		[{ content: 'CHOn did not return an answer.', code: 'empty_response' }, 'empty'],
		[{ content: 'x', code: 'empty_response', finish_reason: 'content_filter' }, 'content_filter'],
		[{ content: 'The response was filtered', status: 400, code: 'ResponsibleAIPolicyViolation' }, 'content_filter'],
		[{ content: { error: { message: 'Blocked', code: 'content_filter' } } }, 'content_filter'],
		[{ content: 'Rate limit is exceeded', status: 429 }, 'rate_limit'],
		[{ content: "This model's maximum context length is 128000 tokens" }, 'context_length'],
		[{ content: 'Unauthorized', status: 401 }, 'auth'],
		[{ content: "Failed to connect to MCP server 'sp_mcp'" }, 'connector'],
		[{ content: 'Token exchange with Entra ID failed (invalid_grant)' }, 'auth'],
		[{ content: 'Model not found', status: 404 }, 'model_unavailable'],
		[{ content: 'Server Connection Error' }, 'network'],
		[{ content: 'Provider returned HTTP 503', status: 503 }, 'network'],
		[{ content: 'boom' }, 'unknown']
	])('%j -> %s', (input, expected) => {
		expect(classifyChatError(input as any)).toBe(expected);
	});
});

describe('explainChatError', () => {
	it('names a cause and a next step, keeps raw details', () => {
		const e = explainChatError(t, { content: 'Rate limit is exceeded', status: 429, code: 'rate_limit_exceeded' });
		expect(e.title).toMatch(/usage limit/);
		expect(e.nextStep).toMatch(/Wait/);
		expect(e.details).toContain('HTTP 429');
		expect(e.canRetry).toBe(true);
	});

	it('treats a stopped answer as a neutral notice', () => {
		const e = explainChatError(t, null, { stopped: true });
		expect(e.kind).toBe('stopped');
		expect(e.neutral).toBe(true);
	});

	it('reads provider error objects', () => {
		expect(errorText({ error: { message: 'nope' } })).toBe('nope');
		expect(errorText({ detail: 'bad' })).toBe('bad');
	});
});
