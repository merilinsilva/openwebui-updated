<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

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

	// Valve values may carry a connection prefix ("azure_ai/claude-sonnet-5-5").
	const findModel = (value: string) =>
		$_models.find((m) => m.id === value) ??
		$_models.find((m) => m.id.split('/').pop() === value.split('/').pop());

	const labelOf = (value: string) => findModel(value)?.name ?? value.split('/').pop();

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
				// Offer only the options this user can access as models (Open WebUI's own access
				// control). If none of them map to a model, the choices aren't model ids: show all.
				const accessible = all.filter((o) => typeof o === 'string' && findModel(o));
				const options = accessible.length > 0 ? accessible : all;

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
	<div class="flex flex-wrap justify-center gap-2 mt-1">
		{#each entries as entry (`${entry.functionId}.${entry.key}`)}
			<label
				class="flex items-center gap-1.5 rounded-full border border-gray-200 dark:border-gray-800 pl-3 pr-1 py-0.5 text-xs text-gray-600 dark:text-gray-300"
				title={entry.description}
			>
				<span>{entry.title}</span>
				<select
					class="bg-transparent text-xs font-medium text-gray-900 dark:text-gray-100 outline-hidden cursor-pointer py-1 pr-1 disabled:opacity-60"
					value={entry.value}
					disabled={saving === `${entry.functionId}.${entry.key}`}
					on:change={(e) => save(entry, e.currentTarget.value)}
				>
					{#each entry.options as option}
						<option value={option} class="bg-white dark:bg-gray-900">{labelOf(option)}</option>
					{/each}
				</select>
			</label>
		{/each}
	</div>
{/if}
