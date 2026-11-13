// Who can see a shared item (prompt, skill, knowledge base, ...), derived from its access grants.
// Used for the ownership badges in the Prompts & skills library and on knowledge bases.

export const ORG_NAME = 'Weidmann';

export type OwnershipTone = 'org' | 'team' | 'mine' | 'shared';
export type Ownership = {
	tone: OwnershipTone;
	// Short badge text, e.g. "Weidmann", "QM Rapperswil", "Mine".
	label: string;
	// Longer form for headers, e.g. "Shared with QM Rapperswil".
	description: string;
};

type Grant = { principal_type?: string; principal_id?: string; permission?: string };
type Translate = (key: string, options?: Record<string, unknown>) => string;

export const getOwnership = (
	item: { user_id?: string; access_grants?: Grant[] | null } | null | undefined,
	currentUserId: string | undefined,
	groupNames: Record<string, string>,
	t: Translate
): Ownership => {
	const grants = item?.access_grants ?? [];

	const isPublic = grants.some(
		(g) => (g.principal_type === 'user' || g.principal_type === 'anyone') && g.principal_id === '*'
	);
	if (isPublic) {
		return {
			tone: 'org',
			label: ORG_NAME,
			description: t('Shared with everyone at {{org}}', { org: ORG_NAME })
		};
	}

	const groupGrants = grants.filter((g) => g.principal_type === 'group');
	if (groupGrants.length > 0) {
		const first = groupNames[groupGrants[0].principal_id ?? ''] ?? t('a team');
		const label = groupGrants.length > 1 ? `${first} +${groupGrants.length - 1}` : first;
		return { tone: 'team', label, description: t('Shared with {{name}}', { name: label }) };
	}

	const sharedWithUsers = grants.some((g) => g.principal_type === 'user' && g.principal_id !== '*');
	if (item?.user_id && item.user_id === currentUserId) {
		return sharedWithUsers
			? { tone: 'shared', label: t('Shared'), description: t('Shared with selected people') }
			: { tone: 'mine', label: t('Mine'), description: t('Private to you') };
	}

	return { tone: 'shared', label: t('Shared'), description: t('Shared with you') };
};

export const ownershipToneClass = (tone: OwnershipTone) =>
	({
		org: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
		team: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
		mine: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
		shared: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
	})[tone];
