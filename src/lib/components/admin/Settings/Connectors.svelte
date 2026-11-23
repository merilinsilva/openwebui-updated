<script lang="ts">
	// CHOn (T08): admin editor for the connector status badges shown on the start screen.
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { tools } from '$lib/stores';
	import { getTools } from '$lib/apis/tools';
	import { getConnectors, setConnectors } from '$lib/apis/configs';

	import AdminSettingSection from './AdminSettingSection.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	type Row = { name: string; description: string; toolIds: string };

	let loaded = false;
	let saving = false;

	let enabled = true;
	let requestAccessUrl = '';
	let rows: Row[] = [];

	const inputClass =
		'w-full rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-1.5 px-3 text-sm outline-hidden focus:border-gray-400 dark:focus:border-gray-600';

	// Tool ids an admin can pick from: connected tool servers first (MCP / OpenAPI).
	$: knownToolIds = (($tools ?? []) as { id: string; name?: string }[])
		.filter((t) => t.id.includes(':'))
		.map((t) => ({ id: t.id, name: t.name ?? t.id }));

	onMount(async () => {
		const res = await getConnectors(localStorage.token).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (res) {
			enabled = res.enabled;
			requestAccessUrl = res.request_access_url ?? '';
			rows = res.items.map((item) => ({
				name: item.name,
				description: item.description ?? '',
				toolIds: (item.tool_ids ?? []).join(', ')
			}));
		}
		if (!$tools) {
			tools.set(await getTools(localStorage.token).catch(() => []));
		}
		loaded = true;
	});

	const save = async () => {
		saving = true;
		const res = await setConnectors(localStorage.token, {
			enabled,
			request_access_url: requestAccessUrl.trim(),
			items: rows
				.filter((r) => r.name.trim())
				.map((r) => ({
					name: r.name.trim(),
					description: r.description.trim(),
					tool_ids: r.toolIds
						.split(',')
						.map((id) => id.trim())
						.filter(Boolean)
				}))
		}).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		saving = false;
		if (res) dispatch('save');
	};
</script>

<form class="flex flex-col h-full justify-between space-y-3 text-sm" on:submit|preventDefault={save}>
	{#if loaded}
		<div class="flex flex-col overflow-y-auto scrollbar-hidden h-full pr-1.5">
			<h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n.t('Connectors')}
			</h2>

			<AdminSettingSection title={$i18n.t('Start screen')} first>
				<AdminSettingRow
					label={$i18n.t('Show connector status')}
					description={$i18n.t(
						'Shows each connector as Connected, Needs sign-in or Request access below the message box on the start screen.'
					)}
				>
					<Switch bind:state={enabled} />
				</AdminSettingRow>

				<AdminSettingField
					label={$i18n.t('Request access link')}
					forId="connectors-request-url"
					description={$i18n.t(
						'Opened from "Request access" badges, for example the TopDesk request form. Leave empty to show a hint instead.'
					)}
				>
					<input
						id="connectors-request-url"
						class={inputClass}
						type="url"
						placeholder="https://…"
						bind:value={requestAccessUrl}
					/>
				</AdminSettingField>
			</AdminSettingSection>

			<AdminSettingSection
				title={$i18n.t('Connectors')}
				description={$i18n.t(
					'A connector is Connected when the user can use one of its tools, Needs sign-in when that tool still needs OAuth, and Request access when the user has none of them.'
				)}
			>
				{#each rows as row, idx}
					<div
						class="flex flex-col gap-2 {idx > 0
							? 'border-t border-gray-100 dark:border-gray-850 pt-3'
							: ''}"
					>
						<div class="flex gap-2">
							<input
								class="{inputClass} @md:w-1/3"
								placeholder={$i18n.t('Name, e.g. Outlook')}
								aria-label={$i18n.t('Connector name')}
								bind:value={row.name}
							/>
							<input
								class={inputClass}
								placeholder={$i18n.t('Short description, e.g. Mail and calendar')}
								aria-label={$i18n.t('Connector description')}
								bind:value={row.description}
							/>
							<button
								type="button"
								class="shrink-0 rounded-lg px-2.5 text-xs text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30"
								on:click={() => (rows = rows.filter((_, i) => i !== idx))}
							>
								{$i18n.t('Remove')}
							</button>
						</div>
						<input
							class="{inputClass} font-mono text-xs"
							placeholder="server:mcp:sp_mcp, server:mcp:other"
							aria-label={$i18n.t('Tool ids')}
							bind:value={row.toolIds}
						/>
					</div>
				{/each}

				<div>
					<button
						type="button"
						class="rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-1.5 text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-850"
						on:click={() => (rows = [...rows, { name: '', description: '', toolIds: '' }])}
					>
						+ {$i18n.t('Add connector')}
					</button>
				</div>

				{#if knownToolIds.length > 0}
					<div class="text-xs text-gray-500 dark:text-gray-400">
						<div class="mb-1">{$i18n.t('Tool ids available on this instance:')}</div>
						<div class="flex flex-wrap gap-1">
							{#each knownToolIds as t (t.id)}
								<code
									class="rounded bg-gray-100 dark:bg-gray-850 px-1.5 py-0.5 text-[0.6875rem]"
									title={t.name}>{t.id}</code
								>
							{/each}
						</div>
					</div>
				{/if}
			</AdminSettingSection>
		</div>

		<div class="flex justify-end pt-3">
			<button
				class="px-4 py-2 text-sm font-semibold bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg flex items-center gap-2 disabled:opacity-60"
				type="submit"
				disabled={saving}
			>
				{$i18n.t('Save')}
				{#if saving}
					<Spinner className="size-4" />
				{/if}
			</button>
		</div>
	{:else}
		<div class="flex h-full justify-center items-center">
			<Spinner className="size-5" />
		</div>
	{/if}
</form>
