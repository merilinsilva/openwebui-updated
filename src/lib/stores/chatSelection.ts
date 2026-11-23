// CHOn (T16): multi-select state for bulk chat actions in the sidebar.
import { writable, get } from 'svelte/store';

export const chatSelectMode = writable(false);
export const selectedChatIds = writable<Set<string>>(new Set());

export const toggleChatSelection = (id: string) => {
	selectedChatIds.update((ids) => {
		const next = new Set(ids);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		return next;
	});
};

export const setChatSelection = (ids: string[]) => {
	selectedChatIds.set(new Set(ids));
};

export const enterChatSelectMode = (initialId?: string) => {
	selectedChatIds.set(new Set(initialId ? [initialId] : []));
	chatSelectMode.set(true);
};

export const exitChatSelectMode = () => {
	chatSelectMode.set(false);
	selectedChatIds.set(new Set());
};

export const getSelectedChatIds = () => Array.from(get(selectedChatIds));
