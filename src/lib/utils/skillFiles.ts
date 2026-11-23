// CHOn (T12): read skills from uploaded files (WG-AI-PLA-00002, section 7.1 / PP-20).
// Supports the Agent Skills format used in the Weidmann repo: a SKILL.md with a YAML
// header (name, description), either on its own or inside a .zip (one folder per skill).
// Open WebUI stores a skill as one Markdown text, so other files in a skill folder
// (scripts, reference docs) cannot be stored and are reported back as ignored.
import JSZip from 'jszip';
import { parse as parseYaml } from 'yaml';

import { formatSkillName, parseFrontmatter, slugify } from '$lib/utils';

export type ParsedSkill = {
	id: string;
	name: string;
	description: string;
	content: string;
	/** File path inside the upload, for messages. */
	source: string;
	/** Other files in the same skill folder that cannot be stored. */
	ignoredFiles: string[];
};

const FRONTMATTER = /^﻿?---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

/** name/description from a SKILL.md header (real YAML, with a simple fallback). */
export const readSkillHeader = (markdown: string): { name?: string; description?: string } => {
	const match = markdown.match(FRONTMATTER);
	if (!match) return {};
	try {
		const data = parseYaml(match[1]);
		if (data && typeof data === 'object') {
			const d = data as Record<string, unknown>;
			return {
				name: typeof d.name === 'string' ? d.name.trim() : undefined,
				description: typeof d.description === 'string' ? d.description.trim() : undefined
			};
		}
	} catch {
		// fall through to the simple line parser
	}
	const fm = parseFrontmatter(markdown) as Record<string, string>;
	return { name: fm.name, description: fm.description };
};

export const skillFromMarkdown = (
	markdown: string,
	fallbackName: string,
	source = '',
	ignoredFiles: string[] = []
): ParsedSkill => {
	const header = readSkillHeader(markdown);
	const rawName = header.name || fallbackName;
	return {
		id: slugify(rawName),
		name: formatSkillName(rawName),
		description: header.description ?? '',
		content: markdown,
		source,
		ignoredFiles
	};
};

const isSkillMd = (path: string) => /(^|\/)skill\.md$/i.test(path);
const dirOf = (path: string) => (path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '');
const baseName = (path: string) => path.split('/').filter(Boolean).pop() ?? path;

/** All skills in a .zip: every SKILL.md is one skill; its folder name is the fallback name. */
export const skillsFromZip = async (data: Blob | ArrayBuffer | Uint8Array, zipName = 'skill') => {
	const zip = await JSZip.loadAsync(data);
	const files = Object.values(zip.files).filter(
		(f) => !f.dir && !f.name.startsWith('__MACOSX/') && !baseName(f.name).startsWith('.')
	);
	const skillFiles = files.filter((f) => isSkillMd(f.name));

	// A zip with a single loose .md (no SKILL.md) is accepted as one skill too.
	if (skillFiles.length === 0) {
		const mds = files.filter((f) => /\.md$/i.test(f.name));
		if (mds.length === 1) skillFiles.push(mds[0]);
	}

	const skills: ParsedSkill[] = [];
	for (const file of skillFiles) {
		const folder = dirOf(file.name);
		const markdown = await file.async('string');
		const ignored = files
			.filter((f) => f !== file && (folder ? f.name.startsWith(folder + '/') : !f.name.includes('/')))
			.map((f) => f.name);
		const fallback = folder ? baseName(folder) : zipName.replace(/\.zip$/i, '');
		skills.push(skillFromMarkdown(markdown, fallback, file.name, ignored));
	}
	return skills;
};

/** Skills in an uploaded .md or .zip file. JSON exports are handled by the caller. */
export const parseSkillFile = async (file: File): Promise<ParsedSkill[]> => {
	const ext = file.name.split('.').pop()?.toLowerCase();
	if (ext === 'zip') {
		return skillsFromZip(await file.arrayBuffer(), file.name);
	}
	if (ext === 'md' || ext === 'markdown') {
		const markdown = await file.text();
		const fallback = /^skill\.md$/i.test(file.name) ? 'skill' : file.name.replace(/\.(md|markdown)$/i, '');
		return [skillFromMarkdown(markdown, fallback, file.name)];
	}
	throw new Error('Unsupported file type. Upload a SKILL.md, a .zip with a skill folder, or a JSON export.');
};
