<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';
	import { slugify, parseFrontmatter, formatSkillName } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { updateSkillAccessGrants } from '$lib/apis/skills';
	import { goto } from '$app/navigation';

	export let onSubmit: Function;
	export let edit = false;
	export let skill = null;
	export let clone = false;
	export let disabled = false;

	const i18n = getContext('i18n');

	let loading = false;

	let name = '';
	let id = '';
	let description = '';
	let content = '';

	let accessGrants = [];
	let showAccessControlModal = false;

	const fieldClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 disabled:bg-gray-50 disabled:text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500 dark:disabled:bg-white/[0.03]';

	// One-line "who can see this" next to the save button.
	$: accessSummary = (() => {
		const grants = accessGrants ?? [];
		if (grants.length === 0) return $i18n.t('Only you can see this skill.');
		if (grants.some((g) => g.principal_id === '*')) {
			return $i18n.t('Everyone at Weidmann can use this skill.');
		}
		return $i18n.t('Shared with selected people or teams.');
	})();

	$: if (!edit && !clone && name) {
		id = slugify(name);
	}

	const handleContentInput = () => {
		if (edit) return;
		const fm = parseFrontmatter(content);
		if (fm.name && !name) {
			name = formatSkillName(fm.name);
		}
		if (fm.description && !description) {
			description = fm.description;
		}
	};

	const submitHandler = async () => {
		if (disabled) {
			toast.error($i18n.t('You do not have permission to edit this skill.'));
			return;
		}
		loading = true;
		if (!edit) id = slugify(id);

		await onSubmit({
			id,
			name,
			description,
			content,
			is_active: true,
			meta: { tags: [] },
			access_grants: accessGrants
		});

		loading = false;
	};

	onMount(async () => {
		if (skill) {
			name = skill.name || '';
			await tick();
			id = skill.id || '';
			description = skill.description || '';
			content = skill.content || '';
			accessGrants = skill?.access_grants === undefined ? [] : skill?.access_grants;
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.skills || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_skills || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && skill?.id) {
			try {
				await updateSkillAccessGrants(localStorage.token, skill.id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<div class="flex h-full w-full min-w-0 flex-col overflow-hidden text-gray-900 dark:text-gray-100">
	<form
		class="mx-auto flex h-full min-h-0 w-full max-w-3xl min-w-0 flex-col"
		on:submit|preventDefault={submitHandler}
	>
		<button
			class="mb-1 flex h-6 w-fit items-center gap-1 rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
			type="button"
			on:click={() => {
				goto('/workspace/skills');
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<div class="flex shrink-0 items-center justify-between gap-2 pb-3">
			<h1 class="truncate text-base font-semibold">
				{edit ? name || $i18n.t('Edit skill') : $i18n.t('New skill')}
			</h1>
			{#if disabled}
				<span class="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-gray-850">
					{$i18n.t('Read Only')}
				</span>
			{/if}
		</div>

		<div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-0.5 pb-1">
			<div class="grid shrink-0 gap-4 sm:grid-cols-2">
				<div class="flex flex-col gap-1.5">
					<label for="skill-name" class="text-sm font-semibold">{$i18n.t('Name')}</label>
					<input
						id="skill-name"
						class={fieldClass}
						type="text"
						placeholder={$i18n.t('e.g. Weidmann document formatting')}
						bind:value={name}
						required
						{disabled}
					/>
				</div>

				<div class="flex flex-col gap-1.5">
					<label for="skill-id" class="text-sm font-semibold">{$i18n.t('Skill ID')}</label>
					<input
						id="skill-id"
						class="{fieldClass} font-mono"
						type="text"
						placeholder={$i18n.t('e.g. weidmann-format')}
						bind:value={id}
						required
						disabled={edit || disabled}
					/>
					{#if !edit}
						<p class="text-xs text-gray-500">{$i18n.t('Filled in from the name. Cannot be changed later.')}</p>
					{/if}
				</div>
			</div>

			<div class="flex shrink-0 flex-col gap-1.5">
				<label for="skill-description" class="text-sm font-semibold">{$i18n.t('Description')}</label>
				<input
					id="skill-description"
					class={fieldClass}
					type="text"
					placeholder={$i18n.t('e.g. Applies Weidmann templates, fonts and colors to Word and PowerPoint files')}
					bind:value={description}
					{disabled}
				/>
				<p class="text-xs text-gray-500">
					{$i18n.t('Shown in the Prompts & skills library. CHOn also uses it to decide when the skill applies.')}
				</p>
			</div>

			<div class="flex min-h-[16rem] flex-1 flex-col gap-1.5">
				<label for="skill-content" class="text-sm font-semibold">{$i18n.t('Instructions')}</label>
				{#if disabled}
					<div
						id="skill-content"
						class="min-h-0 flex-1 overflow-y-auto rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-white/[0.03]"
					>
						<pre class="font-mono text-xs leading-relaxed whitespace-pre-wrap">{content}</pre>
					</div>
				{:else}
					<textarea
						id="skill-content"
						class="{fieldClass} min-h-0 flex-1 resize-none font-mono text-xs leading-relaxed"
						bind:value={content}
						on:input={handleContentInput}
						placeholder={$i18n.t('Enter skill instructions in markdown...')}
						required
					></textarea>
					<p class="text-xs text-gray-500">
						{$i18n.t('Markdown. Paste a SKILL.md here, or upload one from the Prompts & skills library.')}
					</p>
				{/if}
			</div>
		</div>

		{#if !disabled}
			<div class="flex shrink-0 flex-wrap items-center justify-between gap-3 py-3">
				<button
					type="button"
					class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
					title={$i18n.t('Change who can use this skill')}
					on:click={() => (showAccessControlModal = true)}
				>
					<span class="truncate">{accessSummary}</span>
					<span class="shrink-0 underline">{$i18n.t('Change')}</span>
				</button>

				<button
					class="ml-auto flex items-center gap-1.5 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-200"
					type="submit"
					disabled={loading}
				>
					{edit ? $i18n.t('Save') : $i18n.t('Create skill')}
					{#if loading}
						<Spinner className="size-3" />
					{/if}
				</button>
			</div>
		{/if}
	</form>
</div>
