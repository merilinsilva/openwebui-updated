<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getHowToUse, setHowToUse } from '$lib/apis/configs';
	import { howToUseContent } from '$lib/stores';

	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import FormattingButtons from '$lib/components/common/RichTextInput/FormattingButtons.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let loaded = false;
	let saving = false;

	let title = '';
	let initialHtml = '';
	let html = '';

	let editor = null;
	let imageInput: HTMLInputElement;

	// Images are embedded in the guide, so shrink large ones before inserting.
	const MAX_IMAGE_SIZE = 1600;

	const fileToDataUrl = (file: File): Promise<string> =>
		new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(reader.result as string);
			reader.onerror = reject;
			reader.readAsDataURL(file);
		});

	const resizeImage = async (file: File): Promise<string> => {
		const dataUrl = await fileToDataUrl(file);
		// Keep vector and animated images as they are.
		if (['image/svg+xml', 'image/gif'].includes(file.type)) return dataUrl;

		const img = new Image();
		await new Promise((resolve, reject) => {
			img.onload = resolve;
			img.onerror = reject;
			img.src = dataUrl;
		});

		const scale = Math.min(1, MAX_IMAGE_SIZE / Math.max(img.width, img.height));
		if (scale === 1 && file.size < 400 * 1024) return dataUrl;

		const canvas = document.createElement('canvas');
		canvas.width = Math.round(img.width * scale);
		canvas.height = Math.round(img.height * scale);
		canvas.getContext('2d')?.drawImage(img, 0, 0, canvas.width, canvas.height);
		// PNG keeps screenshots crisp; photos compress far better as JPEG.
		return file.type === 'image/png'
			? canvas.toDataURL('image/png')
			: canvas.toDataURL('image/jpeg', 0.85);
	};

	const insertImages = async (currentEditor, files: File[], pos?: number) => {
		for (const file of files) {
			if (!file.type.startsWith('image/')) {
				toast.error($i18n.t('Only images can be added to the guide.'));
				continue;
			}
			try {
				const src = await resizeImage(file);
				currentEditor
					?.chain()
					.focus()
					.insertContentAt(pos ?? currentEditor.state.selection.anchor, {
						type: 'image',
						attrs: { src, alt: file.name }
					})
					.run();
			} catch (error) {
				console.error(error);
				toast.error($i18n.t('Could not read image {{name}}', { name: file.name }));
			}
		}
	};

	const save = async () => {
		saving = true;
		const res = await setHowToUse(localStorage.token, {
			title: title.trim(),
			// An editor with no text still produces "<p></p>"; store that as empty.
			content: editor && editor.isEmpty ? '' : html
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		saving = false;

		if (res) {
			howToUseContent.set(res);
			dispatch('save');
		}
	};

	onMount(async () => {
		const res = await getHowToUse(localStorage.token).catch(() => null);
		title = res?.title ?? '';
		initialHtml = res?.content ?? '';
		html = initialHtml;
		loaded = true;
	});
</script>

<form class="flex flex-col h-full justify-between space-y-3 text-sm" on:submit|preventDefault={save}>
	{#if loaded}
		<div class="flex flex-col gap-3 overflow-y-auto scrollbar-hidden h-full pr-1.5">
			<div>
				<div class="mb-1 text-xs font-medium">{$i18n.t('Button and page title')}</div>
				<input
					class="w-full rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:bg-gray-850 outline-hidden"
					placeholder={$i18n.t('How to use CHOn')}
					bind:value={title}
				/>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t(
						'Shown on the sidebar button and as the heading of the guide. The button is hidden while the guide below is empty.'
					)}
				</div>
			</div>

			<div class="flex flex-col flex-1 min-h-0">
				<div class="mb-1 flex items-center justify-between">
					<div class="text-xs font-medium">{$i18n.t('Guide')}</div>
					<div class="text-xs text-gray-500">
						{$i18n.t('Paste or drag images in, or use the image button.')}
					</div>
				</div>

				<!-- Fixed toolbar so the editor works like a document editor (the bubble menu
				     also appears on text selection). -->
				<div class="mb-1.5 flex flex-wrap items-center gap-1">
					{#if editor}
						<FormattingButtons {editor} />
					{/if}
					<button
						type="button"
						class="flex items-center gap-1 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 px-2.5 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition"
						on:click={() => imageInput?.click()}
					>
						<Photo className="size-4" strokeWidth="1.5" />
						{$i18n.t('Insert image')}
					</button>
					<input
						bind:this={imageInput}
						type="file"
						accept="image/*"
						multiple
						hidden
						on:change={async (e) => {
							const files = Array.from(e.currentTarget.files ?? []);
							e.currentTarget.value = '';
							await insertImages(editor, files);
						}}
					/>
				</div>

				<div
					class="flex-1 min-h-[20rem] rounded-xl border border-gray-100 dark:border-gray-850 px-4 py-3 overflow-y-auto"
				>
					<RichTextInput
						bind:editor
						id="how-to-use-editor"
						className="input-prose-sm min-h-[18rem]"
						json={true}
						html={initialHtml}
						richText={true}
						link={true}
						image={true}
						fileHandler={true}
						showFormattingToolbar={true}
						placeholder={$i18n.t('Write the guide users will see…')}
						onChange={(content) => {
							html = content.html;
						}}
						onFileDrop={(currentEditor, files, pos) => insertImages(currentEditor, files, pos)}
						onFilePaste={(currentEditor, files, htmlContent) => {
							// Pasted HTML (e.g. from a web page) is handled by the editor itself.
							if (htmlContent) return false;
							insertImages(currentEditor, files);
						}}
					/>
				</div>
			</div>
		</div>

		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 disabled:opacity-60"
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
