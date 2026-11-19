<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { slide } from 'svelte/transition';
	import { displayModelName, modelDescription } from '$lib/utils/modelNames';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	import { models as _models } from '$lib/stores';
	import {
		getUserValvesById,
		getUserValvesSpecById,
		updateUserValvesById
	} from '$lib/apis/functions';

	const i18n = getContext('i18n');

	// Shows the fixed-choice user valves of the filters attached to this model (e.g. the
	// Base Model Router's BASE_MODEL) as dropdowns, so users don't have to go through
	// Controls > Valves > Functions > <filter>.
	export let model = null;

	type Entry = {
		functionId: string;
		key: string;
		title: string;
		description: string;
		options: string[];
		value: string;
		values: Record<string, unknown>;
	};

	let entries: Entry[] = [];
	let saving = '';
	let loadToken = 0;

	// A Literal/enum valve comes through as `enum`, or as a $ref to an enum in $defs.
	const optionsOf = (prop, spec): string[] | null => {
		if (Array.isArray(prop?.enum)) return prop.enum;
		const ref = prop?.$ref ?? prop?.allOf?.[0]?.$ref;
		if (typeof ref === 'string') {
			const def = spec?.$defs?.[ref.split('/').pop()];
			if (Array.isArray(def?.enum)) return def.enum;
		}
		return null;
	};

	// Valve values may carry a connection prefix ("azure_ai/claude-sonnet-5-5") or differ in
	// case from the model entry ("azure_ai/FW-Kimi-K3" vs "fw-kimi-k3"), so match loosely.
	const bareId = (id: string) => `${id ?? ''}`.split('/').pop()?.toLowerCase() ?? '';
	const findModel = (value: string) =>
		$_models.find((m) => m.id === value) ??
		$_models.find((m) => m.id.toLowerCase() === `${value}`.toLowerCase()) ??
		$_models.find((m) => bareId(m.id) === bareId(value));

	// "auto" is not a model: the router picks the user's group default for it.
	const AUTO = 'auto';

	// Admin-set model name (Admin Settings > Models), or a readable form of the id.
	const labelOf = (value: string) =>
		value === AUTO ? $i18n.t('Auto') : displayModelName(findModel(value), value);
	// "What it is used for": the model's description from Admin Settings > Models.
	const descriptionOf = (value: string) =>
		value === AUTO
			? $i18n.t("Uses your team's default model.")
			: modelDescription(findModel(value));

	let openKey = '';

	const load = async (m) => {
		const token = ++loadToken;
		const filterIds: string[] = m?.info?.meta?.filterIds ?? [];
		const next: Entry[] = [];

		for (const functionId of filterIds) {
			const spec = await getUserValvesSpecById(localStorage.token, functionId).catch(() => null);
			if (!spec?.properties) continue;
			const values = (await getUserValvesById(localStorage.token, functionId).catch(() => null)) ?? {};

			for (const [key, prop] of Object.entries<any>(spec.properties)) {
				const all = optionsOf(prop, spec);
				if (!all || all.length === 0) continue;

				const value = (values[key] ?? prop.default ?? all[0]) as string;
				// The filter's own list decides what users may pick (it handles restrictions
				// itself), so show every choice, including non-model values such as "auto".
				const options = all.filter((o) => typeof o === 'string');

				next.push({
					functionId,
					key,
					title: prop.title ?? key,
					description: prop.description ?? '',
					options: options.includes(value) ? options : [value, ...options],
					value,
					values
				});
			}
		}

		// Ignore results from a model the user has already switched away from.
		if (token === loadToken) entries = next;
	};

	$: load(model);

	const save = async (entry: Entry, value: string) => {
		const previous = entry.value;
		entry.value = value;
		entries = entries;
		saving = `${entry.functionId}.${entry.key}`;

		const res = await updateUserValvesById(localStorage.token, entry.functionId, {
			...entry.values,
			[entry.key]: value
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		saving = '';

		if (res) {
			entry.values = { ...entry.values, [entry.key]: value };
			toast.success($i18n.t('{{title}} set to {{value}}', { title: entry.title, value: labelOf(value) }));
		} else {
			entry.value = previous;
		}
		entries = entries;
	};
</script>

{#if entries.length > 0}
	<div class="flex w-full flex-col items-center gap-2 mt-1 px-5">
		{#each entries as entry (`${entry.functionId}.${entry.key}`)}
			{@const key = `${entry.functionId}.${entry.key}`}
			<button
				type="button"
				class="flex items-center gap-1.5 rounded-full border border-gray-200 dark:border-gray-800 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition disabled:opacity-60"
				title={entry.description}
				aria-expanded={openKey === key}
				disabled={saving === key}
				on:click={() => (openKey = openKey === key ? '' : key)}
			>
				<span>{entry.title}</span>
				<span class="font-medium text-gray-900 dark:text-gray-100">{labelOf(entry.value)}</span>
				<ChevronDown className="size-3 transition {openKey === key ? 'rotate-180' : ''}" strokeWidth="2" />
			</button>

			{#if openKey === key}
				<div
					class="grid w-full max-w-3xl grid-cols-1 @md:grid-cols-2 gap-2 text-left"
					transition:slide={{ duration: 150 }}
				>
					{#each entry.options as option}
						{@const selected = option === entry.value}
						<button
							type="button"
							class="flex flex-col rounded-2xl border px-4 py-3 transition {selected
								? 'border-gray-900 dark:border-gray-100 bg-gray-50 dark:bg-gray-850'
								: 'border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850'}"
							aria-pressed={selected}
							on:click={async () => {
								openKey = '';
								if (!selected) await save(entry, option);
							}}
						>
							<span class="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
								{labelOf(option)}
							</span>
							{#if descriptionOf(option)}
								<span class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
									{descriptionOf(option)}
								</span>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		{/each}
	</div>
{/if}
