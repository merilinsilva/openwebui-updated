<script>
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { updateToolAccessGrants } from '$lib/apis/tools';

	import { extractFrontmatter, formatSkillName, nameToId } from '$lib/utils';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';

	let formElement = null;
	let loading = false;

	let showConfirm = false;
	let showAccessControlModal = false;

	export let edit = false;
	export let clone = false;

	export let onSave = /** @param {any} _value */ async (_value) => {};

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	export let accessGrants = [];

	let _content = '';

	$: if (content) {
		updateContent();
	}

	const updateContent = () => {
		_content = content;
	};

	$: if (name && !edit && !clone) {
		id = nameToId(name);
	}

	let codeEditor;
	let boilerplate = `import os
import requests
from datetime import datetime
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints and descriptions
	
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include a descrption for __user__ as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(
        self,
        equation: str = Field(
            ..., description="The mathematical equation to calculate."
        ),
    ) -> str:
        """
        Calculate the result of an equation.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(
        self,
        city: str = Field(
            "New York, NY", description="Get the current weather for a given city."
        ),
    ) -> str:
        """
        Get the current weather for a given city.
        """

        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
`;

	const saveHandler = async () => {
		loading = true;
		try {
			await onSave({
				id,
				name,
				meta,
				content,
				access_grants: accessGrants
			});
		} finally {
			loading = false;
		}
	};

	const submitHandler = async () => {
		if (codeEditor) {
			content = _content;
			await tick();

			const res = await codeEditor.formatPythonCodeHandler();
			await tick();

			content = _content;
			await tick();

			if (!res) {
				console.warn('Code formatting failed or was skipped, saving unformatted code');
			}

			saveHandler();
		}
	};

	// CHOn form styles (same as the skill and prompt forms).
	const fieldClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 disabled:bg-gray-50 disabled:text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500 dark:disabled:bg-white/[0.03]';

	// One-line "who can use this" next to the save button.
	$: accessSummary =
		(accessGrants ?? []).length === 0
			? $i18n.t('Only you can use this tool.')
			: (accessGrants ?? []).some((g) => g.principal_id === '*')
				? $i18n.t('Everyone at Weidmann can use this tool.')
				: $i18n.t('Shared with selected people or teams.');
</script>

<AccessControlModal
	itemName={name}
	subtitle={$i18n.t('Tool')}
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.tools || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_tools || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && id) {
			try {
				await updateToolAccessGrants(localStorage.token, id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<div class="flex h-full w-full min-w-0 flex-col overflow-hidden text-gray-900 dark:text-gray-100">
	<form
		bind:this={formElement}
		class="mx-auto flex h-full min-h-0 w-full max-w-5xl min-w-0 flex-col"
		on:submit|preventDefault={() => {
			if (edit) {
				submitHandler();
			} else {
				showConfirm = true;
			}
		}}
	>
		<button
			class="mb-1 flex h-6 w-fit items-center gap-1 rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
			type="button"
			on:click={() => {
				goto('/workspace/tools');
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<h1 class="shrink-0 truncate pb-3 text-base font-semibold">
			{edit ? name || $i18n.t('Edit tool') : $i18n.t('New tool')}
		</h1>

		<div class="flex min-h-0 flex-1 flex-col gap-4 px-0.5 pb-1">
			<div class="grid shrink-0 gap-4 sm:grid-cols-2">
				<div class="flex flex-col gap-1.5">
					<label for="tool-name" class="text-sm font-semibold">{$i18n.t('Name')}</label>
					<input
						id="tool-name"
						class={fieldClass}
						type="text"
						placeholder={$i18n.t('e.g. SAP order lookup')}
						bind:value={name}
						required
					/>
				</div>

				<div class="flex flex-col gap-1.5">
					<label for="tool-id" class="text-sm font-semibold">{$i18n.t('Tool ID')}</label>
					<input
						id="tool-id"
						class="{fieldClass} font-mono"
						type="text"
						placeholder={$i18n.t('e.g. sap_order_lookup')}
						bind:value={id}
						required
						disabled={edit}
					/>
					{#if !edit}
						<p class="text-xs text-gray-500">{$i18n.t('Cannot be changed later.')}</p>
					{/if}
				</div>
			</div>

			<div class="flex shrink-0 flex-col gap-1.5">
				<label for="tool-description" class="text-sm font-semibold">{$i18n.t('Description')}</label>
				<input
					id="tool-description"
					class={fieldClass}
					type="text"
					placeholder={$i18n.t('e.g. Looks up order status and delivery dates in SAP')}
					bind:value={meta.description}
					required
				/>
				<p class="text-xs text-gray-500">
					{$i18n.t('Shown in the tool list and when attaching tools to a model.')}
				</p>
			</div>

			<div
				class="shrink-0 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
				role="note"
			>
				<span class="font-semibold">{$i18n.t('Tools run code on the server.')}</span>
				{$i18n.t('Only install tools from sources you trust.')}
			</div>

			<div class="flex min-h-[16rem] flex-1 flex-col gap-1.5">
				<div class="flex items-center justify-between gap-2">
					<div class="text-sm font-semibold">{$i18n.t('Code')}</div>
					<div class="text-xs text-gray-500">{$i18n.t('Python · Ctrl+S to save')}</div>
				</div>
				<div
					class="min-h-0 flex-1 overflow-hidden rounded-lg border border-gray-300 focus-within:border-gray-500 dark:border-gray-700 dark:focus-within:border-gray-500"
				>
					<CodeEditor
						bind:this={codeEditor}
						value={content}
						lang="python"
						{boilerplate}
						className="text-[0.6875rem]"
						onChange={(e) => {
							_content = e;
							if (!edit) {
								const fm = extractFrontmatter(e);
								if (fm.title && !name) {
									name = formatSkillName(fm.title);
									id = nameToId(fm.title);
								}
								if (fm.description && !meta.description) {
									meta = { ...meta, description: fm.description };
								}
							}
						}}
						onSave={async () => {
							if (formElement) {
								formElement.requestSubmit();
							}
						}}
					/>
				</div>
			</div>
		</div>

		<div class="flex shrink-0 flex-wrap items-center justify-between gap-3 py-3">
			<button
				type="button"
				class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
				title={$i18n.t('Change who can use this tool')}
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
				{edit ? $i18n.t('Save') : $i18n.t('Create tool')}
				{#if loading}
					<Spinner className="size-3" />
				{/if}
			</button>
		</div>
	</form>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>
					{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}
				</li>
				<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
