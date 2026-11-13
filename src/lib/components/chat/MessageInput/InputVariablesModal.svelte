<script lang="ts">
	import { getContext, tick } from 'svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import MapSelector from '$lib/components/common/Valves/MapSelector.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let variables = {};
	// Name of the prompt being filled in; empty when unknown (e.g. pasted text).
	export let promptName = '';
	// The prompt text with its {{variables}}, used for "Preview prompt".
	export let template = '';
	// Set for non-prompt forms (e.g. "Chat Variables"): plain title, no prompt badge or wording.
	export let title = '';

	export let onSave = (e) => {};

	$: isPromptForm = !title;

	let loading = true;
	let variableValues = {};
	let variablesKey = '';
	let showPreview = false;

	const inputClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-gray-500 dark:scheme-dark';

	// {{meeting_title}} -> "Meeting title"; an explicit label in the definition wins.
	const humanize = (name: string) => {
		const words = name
			.replace(/([a-z0-9])([A-Z])/g, '$1 $2')
			.replace(/[_\-.]+/g, ' ')
			.trim()
			.toLowerCase();
		return words ? words.charAt(0).toUpperCase() + words.slice(1) : name;
	};
	const getVariableLabel = (variable) => variables[variable]?.label ?? humanize(variable);
	const getVariablesKey = (value) => JSON.stringify(value ?? {});

	// Same substitution the chat input applies (RichTextInput.replaceVariables).
	$: preview = (template ?? '').replace(/{{\s*([^|}]+)(?:\|[^}]*)?\s*}}/g, (match, name) => {
		const value = variableValues[name.trim()];
		return value === undefined || value === '' ? match : String(value);
	});

	const submitHandler = async () => {
		// Normalize Windows CRLF (\r\n) to LF (\n) for all string values
		// Build a new object to avoid mutating the reactive variableValues proxy
		const result = {};
		for (const key of Object.keys(variableValues)) {
			if (typeof variableValues[key] === 'string') {
				result[key] = variableValues[key].replace(/\r\n/g, '\n');
			} else {
				result[key] = variableValues[key];
			}
		}
		onSave(result);
		show = false;
	};

	const init = async () => {
		loading = true;
		showPreview = false;
		const newValues = {};
		const keys = Object.keys(variables ?? {});
		for (const key of keys) {
			const variable = variables[key];
			if (variable?.default !== undefined) {
				newValues[key] = variable.default;
			} else {
				newValues[key] = '';
			}
		}
		variableValues = newValues;
		loading = false;

		await tick();

		document.getElementById('input-variable-0')?.focus();
	};

	$: if (!show) {
		variablesKey = '';
	}

	$: if (show) {
		const key = getVariablesKey(variables);
		if (key !== variablesKey) {
			variablesKey = key;
			init();
		}
	}
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-900 rounded-2xl">
	<form
		class="flex flex-col px-5 pt-4 pb-4 text-gray-900 dark:text-gray-100"
		on:submit|preventDefault={submitHandler}
	>
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<div class="flex min-w-0 items-center gap-2">
					{#if isPromptForm}
						<span
							class="shrink-0 rounded border border-gray-300 px-1.5 text-[0.6875rem] leading-4 text-gray-600 dark:border-gray-600 dark:text-gray-400"
						>
							{$i18n.t('Prompt')}
						</span>
					{/if}
					<h2 class="truncate text-base font-semibold">
						{isPromptForm ? promptName || $i18n.t('Fill in the prompt') : title}
					</h2>
				</div>
				{#if isPromptForm}
					<p class="mt-1 text-xs text-gray-500">
						{$i18n.t('Fill in the details. CHOn inserts them into the prompt.')}
					</p>
				{/if}
			</div>
			<button
				class="shrink-0 rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="mt-4 flex max-h-[60dvh] flex-col gap-3 overflow-y-auto">
			{#if loading}
				<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
			{:else}
				{#each Object.keys(variables) as variable, idx}
					{@const { type, ...variableAttributes } = variables[variable] ?? {}}

					<div class="flex flex-col gap-1.5">
						{#if variables[variable]?.type !== 'checkbox'}
							<label for="input-variable-{idx}" class="text-sm font-semibold">
								{getVariableLabel(variable)}
								{#if variables[variable]?.required ?? false}
									<span class="ml-1 text-xs font-normal text-gray-500">* {$i18n.t('required')}</span>
								{/if}
							</label>
						{/if}

						{#if variables[variable]?.type === 'select'}
							<select
								class={inputClass}
								bind:value={variableValues[variable]}
								id="input-variable-{idx}"
							>
								<option value="" disabled>
									{variables[variable]?.placeholder ?? $i18n.t('Select an option')}
								</option>
								{#each variables[variable]?.options ?? [] as option}
									<option value={option}>{option}</option>
								{/each}
							</select>
						{:else if variables[variable]?.type === 'checkbox'}
							<label class="flex items-center gap-2 text-sm font-semibold">
								<input
									type="checkbox"
									bind:checked={variableValues[variable]}
									class="size-4 cursor-pointer rounded border border-gray-300 dark:border-gray-700"
									id="input-variable-{idx}"
									{...variableAttributes}
								/>
								{getVariableLabel(variable)}
								{#if variables[variable]?.required ?? false}
									<span class="text-xs font-normal text-gray-500">* {$i18n.t('required')}</span>
								{/if}
							</label>
						{:else if variables[variable]?.type === 'color'}
							<div class="flex items-center gap-2">
								<input
									type="color"
									class="size-9 shrink-0 cursor-pointer rounded-lg border border-gray-300 dark:border-gray-700"
									value={variableValues[variable]}
									id="input-variable-{idx}"
									on:input={(e) => {
										// Convert the color value to uppercase immediately
										variableValues[variable] = e.target.value.toUpperCase();
									}}
									{...variableAttributes}
								/>
								<input
									type="text"
									class={inputClass}
									placeholder={$i18n.t('Enter hex color (e.g. #FF0000)')}
									bind:value={variableValues[variable]}
									autocomplete="off"
									required={variables[variable]?.required ?? false}
								/>
							</div>
						{:else if variables[variable]?.type === 'date'}
							<input
								type="date"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'datetime-local'}
							<input
								type="datetime-local"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'email'}
							<input
								type="email"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'month'}
							<input
								type="month"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'number'}
							<input
								type="number"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'range'}
							<div class="flex items-center gap-3">
								<input
									type="range"
									bind:value={variableValues[variable]}
									class="flex-1"
									id="input-variable-{idx}"
									{...variableAttributes}
								/>
								<input
									type="text"
									class="{inputClass} !w-20 text-right"
									placeholder={$i18n.t('Enter value')}
									bind:value={variableValues[variable]}
									autocomplete="off"
									required={variables[variable]?.required ?? false}
								/>
							</div>
						{:else if variables[variable]?.type === 'tel'}
							<input
								type="tel"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'text'}
							<input
								type="text"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'time'}
							<input
								type="time"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'url'}
							<input
								type="url"
								class={inputClass}
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
								{...variableAttributes}
							/>
						{:else if variables[variable]?.type === 'map'}
							<!-- EXPERIMENTAL INPUT TYPE, DO NOT USE IN PRODUCTION -->
							<div class="flex flex-col items-center gap-1">
								<MapSelector
									setViewLocation={((variableValues[variable] ?? '').includes(',') ?? false)
										? variableValues[variable].split(',')
										: null}
									onClick={(value) => {
										variableValues[variable] = value;
									}}
								/>
								<input
									type="text"
									class={inputClass}
									placeholder={$i18n.t('Enter coordinates (e.g. 51.505, -0.09)')}
									bind:value={variableValues[variable]}
									autocomplete="off"
									required={variables[variable]?.required ?? false}
								/>
							</div>
						{:else}
							<textarea
								class="{inputClass} min-h-[5rem] resize-y"
								placeholder={variables[variable]?.placeholder ?? ''}
								bind:value={variableValues[variable]}
								autocomplete="off"
								id="input-variable-{idx}"
								required={variables[variable]?.required ?? false}
							/>
						{/if}
					</div>
				{/each}
			{/if}

			{#if showPreview && template}
				<div class="rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-850">
					<div class="text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase">
						{$i18n.t('Preview')}
					</div>
					<div class="mt-1 max-h-48 overflow-y-auto text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">
						{preview}
					</div>
				</div>
			{/if}
		</div>

		<div class="mt-4 flex items-center justify-between gap-2">
			{#if template}
				<button
					class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
					type="button"
					aria-pressed={showPreview}
					on:click={() => (showPreview = !showPreview)}
				>
					{showPreview ? $i18n.t('Hide preview') : $i18n.t('Preview prompt')}
				</button>
			{:else}
				<span></span>
			{/if}

			<button
				class="rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
				type="submit"
			>
				{isPromptForm ? $i18n.t('Use prompt') : $i18n.t('Save')}
			</button>
		</div>
	</form>
</Modal>
