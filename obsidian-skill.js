/**
 * OWL-AGENT Scraper — Obsidian Skill
 * =====================================
 * Place this file in your vault's .obsidian/skills/ folder.
 *
 * Dependencies (install in vault root):
 *   npm init -y && npm install turndown
 *
 * Usage:
 *   1. Ensure owl_server.py is running on port 60000
 *   2. Cmd/Ctrl+P → "OWL Scraper: Fetch URL"
 *   3. Enter URL → markdown note is created automatically
 *
 * Requires: Obsidian v1.5+, obsidian-skills plugin
 */

const { Notice, requestUrl } = require('obsidian');
const TurndownService = require('turndown');

const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  emDelimiter: '*',
});

/**
 * Sanitise a URL into a filename-safe string.
 */
function urlToTitle(url) {
  try {
    const u = new URL(url);
    const date = new Date().toISOString().slice(0, 10);
    return `${u.hostname} ${date}`.replace(/[<>:"/\\|?*]/g, '_').slice(0, 200);
  } catch {
    return `scraped-${Date.now()}`;
  }
}

/**
 * Fetch a URL through OWL-AGENT and return the parsed response.
 */
async function fetchViaOwlAgent(url, options = {}) {
  const apiUrl = options.apiUrl || 'http://127.0.0.1:60000/fetch';

  const resp = await requestUrl({
    url: apiUrl,
    method: 'POST',
    contentType: 'application/json',
    body: JSON.stringify({
      url: url,
      method: options.method || 'GET',
      headers: options.headers || {},
      browser: options.browser || false,
      wait_for: options.waitFor || null,
      timeout: options.timeout || 30,
    }),
  });

  if (resp.status !== 200) {
    throw new Error(`OWL-AGENT returned status ${resp.status}: ${resp.text}`);
  }

  return resp.json;
}

module.exports = {
  name: 'OWL Scraper',
  description: 'Fetch any URL through OWL-AGENT and save as a markdown note in your vault',
  version: '1.0.0',

  async execute(args, context) {
    const url = args.url;
    if (!url) {
      new Notice('❌ Please provide a URL.');
      return;
    }

    const app = context.app;
    if (!app) {
      new Notice('❌ No Obsidian app context available.');
      return;
    }

    try {
      new Notice(`🦉 Fetching ${url}...`);

      // 1. Fetch via OWL-AGENT
      const data = await fetchViaOwlAgent(url, {
        browser: args.browser || false,
        waitFor: args.waitFor || null,
        timeout: args.timeout || 30,
      });

      // 2. Convert to markdown
      const contentType = (data.headers && data.headers['content-type']) || '';
      let markdown = data.content || '';

      if (contentType.includes('text/html')) {
        markdown = turndown.turndown(markdown);
      }

      // 3. Build frontmatter
      const title = urlToTitle(url);
      const frontmatter = [
        '---',
        `title: "${title}"`,
        `source: "${url}"`,
        `scraped: "${new Date().toISOString()}"`,
        `status: ${data.status}`,
        `content_type: "${contentType}"`,
        `latency: ${data.latency_seconds || 'unknown'}s`,
        'tags: [scraped, web]',
        '---',
        '',
      ].join('\n');

      const noteContent = frontmatter + markdown;

      // 4. Write to vault
      const fileName = `${title}.md`;
      const existing = app.vault.getAbstractFileByPath(fileName);

      if (existing) {
        await app.vault.modify(existing, noteContent);
        new Notice(`✅ Updated: ${fileName}`);
      } else {
        await app.vault.create(fileName, noteContent);
        new Notice(`✅ Created: ${fileName}`);
      }

    } catch (error) {
      new Notice(`❌ OWL Scraper error: ${error.message}`);
      console.error('OWL Scraper error:', error);
    }
  },
};
