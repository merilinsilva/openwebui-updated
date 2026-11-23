// CHOn (T16): trimmed user settings for standard users (WG-AI-PLA-00002, section 9, PP-24).
// Admins always see the full Open WebUI settings.
//
// To show a hidden tab again for everyone, remove its id from HIDDEN_SETTINGS_TABS.
// Hidden rows inside the Interface tab are listed in src/app.css
// (search for "chon-trimmed-settings").

/** Personal settings tabs hidden from non-admin users (ids from SettingsModal.svelte). */
export const HIDDEN_SETTINGS_TABS: string[] = ['shortcuts', 'audio', 'connections', 'usage', 'about'];

/** True when the user should get the short, Weidmann-specific settings page. */
export const useTrimmedSettings = (user: { role?: string } | null | undefined): boolean =>
	user?.role !== 'admin';

export const isSettingsTabVisible = (
	tabId: string,
	user: { role?: string } | null | undefined
): boolean => !(useTrimmedSettings(user) && HIDDEN_SETTINGS_TABS.includes(tabId));
