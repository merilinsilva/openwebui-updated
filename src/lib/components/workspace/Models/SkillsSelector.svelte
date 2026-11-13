<script lang="ts">
	import XMark from '$lib/components/icons/XMark.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	import { getContext } from 'svelte';

	type Skill = {
		id: string;
		name?: string;
		description?: string;
		is_active?: boolean;
	};

	export let skills: Skill[] = [];
	export let selectedSkillIds: string[] = [];

	const i18n = getContext('i18n') as any;

	$: activeSkills = skills.filter((skill) => skill.is_active !== false);
	$: selectedSkills = activeSkills.filter((skill) => selectedSkillIds.includes(skill.id));

	const toggleSkill = (skill: Skill) => {
		selectedSkillIds = selectedSkillIds.includes(skill.id)
			? selectedSkillIds.filter((id) => id !== skill.id)
			: [...selectedSkillIds, skill.id];
	};
</script>

<div>
	<div class="mb-2 flex w-full items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Skills')}</div>
			<p class="text-xs text-gray-500">{$i18n.t('Instructions the model follows for specific jobs, e.g. Weidmann document formatting.')}</p>
		</div>

		{#if activeSkills.length > 0}
			<TypeaheadSelector
				id="model-skills-selector"
				items={activeSkills}
				selectedIds={selectedSkillIds}
				placeholder={$i18n.t('Search skills')}
				triggerLabel={$i18n.t('Add skill')}
				emptyLabel={$i18n.t('No skills found')}
				variant="dropdown"
				on:select={(e) => {
					toggleSkill(e.detail);
				}}
				on:enableall={(e) => {
					selectedSkillIds = [
						...new Set([...selectedSkillIds, ...e.detail.map((skill) => skill.id)])
					];
				}}
			/>
		{/if}
	</div>

	<div class="flex flex-col mb-1">
		{#if activeSkills.length > 0}
			<div class="flex flex-wrap items-center gap-1.5">
				{#each selectedSkills as skill (skill.id)}
					<span class="inline-flex max-w-full items-center gap-1 rounded-full border border-gray-300 py-0.5 pr-1 pl-2.5 text-xs text-gray-800 dark:border-gray-700 dark:text-gray-200" title={skill.description ?? skill.id}>
						<span class="truncate">{skill.name}</span>
						<button
							type="button"
							class="rounded-full p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
							aria-label={$i18n.t('Remove {{name}}', { name: skill.name })}
							on:click={() => {
								selectedSkillIds = selectedSkillIds.filter((id) => id !== skill.id);
							}}
						>
							<XMark className="size-3" />
						</button>
					</span>
				{/each}

				{#if selectedSkills.length > 0}
					<button
						type="button"
						class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
						on:click={() => {
							selectedSkillIds = [];
						}}
					>
						{$i18n.t('Remove all')}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if activeSkills.length === 0}
		<div class="text-xs text-gray-500">{$i18n.t('No skills available yet. Add them in Workspace > Skills first.')}</div>
	{/if}
</div>
