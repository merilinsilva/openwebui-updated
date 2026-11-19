// Readable model names for pickers. Connection models often have their raw id as name
// ("azure_ai/claude-haiku-5-5"); turn those into "Claude Haiku 5.5".

const UPPERCASE_WORDS = new Set(['gpt', 'ai', 'llm', 'api', 'r1', 'v3', 'v4']);

export const prettifyModelId = (id: string = ''): string => {
	const bare = id.split('/').pop() ?? id;
	const tokens = bare.split(/[-_\s]+/).filter(Boolean);

	const words: string[] = [];
	for (const token of tokens) {
		// Join version parts: "5", "5" -> "5.5".
		const previous = words[words.length - 1];
		if (/^\d+$/.test(token) && previous && /^\d+(\.\d+)*$/.test(previous)) {
			words[words.length - 1] = `${previous}.${token}`;
			continue;
		}
		if (UPPERCASE_WORDS.has(token.toLowerCase())) {
			words.push(token.toUpperCase());
		} else if (/^[a-z]/.test(token)) {
			words.push(token.charAt(0).toUpperCase() + token.slice(1));
		} else {
			words.push(token);
		}
	}
	return words.join(' ') || id;
};

// The admin-set display name, unless it is just the id; then a prettified id.
export const displayModelName = (model: { id?: string; name?: string } | null | undefined, fallbackId = '') => {
	const id = model?.id ?? fallbackId;
	const name = (model?.name ?? '').trim();
	if (name && name !== id && name !== id.split('/').pop()) return name;
	return prettifyModelId(id);
};

// Plain-text description from a model's metadata (first paragraph, markdown stripped).
export const modelDescription = (model): string =>
	`${model?.info?.meta?.description ?? ''}`
		.replace(/[#*_`>[\]()]/g, '')
		.replace(/\s+/g, ' ')
		.trim();
