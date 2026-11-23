<script lang="ts">
	// CHOn (T08): connector status badges on the start screen (WG-AI-PLA-00002, section 6, PP-03).
	// Each connector (Outlook, SharePoint, Bee360, ...) is configured in Admin Settings > Connectors
	// and maps to tool ids. Status comes from the user's own tool list:
	//   not in the list          -> Request access (no permission yet)
	//   authenticated === false  -> Needs sign-in (OAuth not done)
	//   otherwise                -> Connected
	import { getContext, onMount } from 'svelte';
	import { tools } from '$lib/stores';
	import { getTools } from '$lib/apis/tools';
	import { getConnectors, type ConnectorsConfig } from '$lib/apis/configs';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let oauthRedirectHandler: Function = () => {};

	type Status = 'connected' | 'signin' | 'request';
	type Tool = { id: string; name?: string; authenticated?: boolean };

	let config: ConnectorsConfig | null = null;

	onMount(async () => {
		config = await getConnectors(localStorage.token).catch(() => null);
		if (config?.enabled && config.items.length > 0 && !$tools) {
			tools.set(await getTools(localStorage.token).catch(() => []));
		}
	});

	const toOAuthTool = (tool: Tool) => {
		const parts = tool.id.split(':');
		return {
			id: tool.id,
			name: tool.name ?? tool.id,
			serverId: parts.at(-1) ?? tool.id,
			authType: parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null
		};
	};

	$: connectors = (config?.enabled ? config.items : []).map((item) => {
		const matched = (($tools ?? []) as Tool[]).filter((t) => item.tool_ids.includes(t.id));
		const unauthed = matched.find((t) => t.authenticated === false);
		const status: Status =
			matched.length === 0 ? 'request' : unauthed ? 'signin' : 'connected';
		return { ...item, status, signInTool: unauthed ? toOAuthTool(unauthed) : null };
	});

	const label = (status: Status) =>
		status === 'connected'
			? $i18n.t('Connected')
			: status === 'signin'
				? $i18n.t('Needs sign-in')
				: $i18n.t('Request access');

	const hint = (c: { name: string; description: string; status: Status }) => {
		const what = c.description ? `${c.name}: ${c.description}. ` : `${c.name}. `;
		if (c.status === 'connected') {
			return what + $i18n.t('CHOn can use it in your chats.');
		}
		if (c.status === 'signin') {
			return what + $i18n.t('Sign in once with your Weidmann account so CHOn can use it.');
		}
		return (
			what +
			(config?.request_access_url
				? $i18n.t('You do not have access yet. Open a TopDesk request to get it.')
				: $i18n.t('You do not have access yet. Ask the CHOn team for access.'))
		);
	};

	const badgeClass = {
		connected:
			'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300',
		signin:
			'border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300 dark:hover:bg-amber-950/70',
		request:
			'border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-850'
	};

	const dotClass = {
		connected: 'bg-emerald-500',
		signin: 'bg-amber-500',
		request: 'bg-gray-400 dark:bg-gray-600'
	};
</script>

{#if connectors.length > 0}
	<div
		class="flex flex-wrap items-center gap-1.5 text-left"
		role="list"
		aria-label={$i18n.t('Connector status')}
	>
		<span
			class="text-[0.6875rem] font-medium tracking-wide uppercase text-gray-400 dark:text-gray-500 mr-1"
		>
			{$i18n.t('Connectors')}
		</span>

		{#each connectors as c (c.name)}
			<div role="listitem">
				<Tooltip content={hint(c)} allowHTML={false} placement="top">
					{#if c.status === 'signin' && c.signInTool}
						<button
							type="button"
							class="flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs transition {badgeClass.signin}"
							on:click={() => oauthRedirectHandler(c.signInTool)}
						>
							<span class="size-1.5 rounded-full {dotClass.signin}" aria-hidden="true"></span>
							<span class="font-medium">{c.name}</span>
							<span class="opacity-80">· {label(c.status)}</span>
						</button>
					{:else if c.status === 'request' && config?.request_access_url}
						<a
							href={config.request_access_url}
							target="_blank"
							rel="noopener noreferrer"
							class="flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs transition {badgeClass.request}"
						>
							<span class="size-1.5 rounded-full {dotClass.request}" aria-hidden="true"></span>
							<span class="font-medium">{c.name}</span>
							<span class="opacity-80">· {label(c.status)} ↗</span>
						</a>
					{:else}
						<span
							class="flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs {badgeClass[
								c.status
							]}"
						>
							<span class="size-1.5 rounded-full {dotClass[c.status]}" aria-hidden="true"></span>
							<span class="font-medium">{c.name}</span>
							<span class="opacity-80">· {label(c.status)}</span>
						</span>
					{/if}
				</Tooltip>
			</div>
		{/each}
	</div>
{/if}
