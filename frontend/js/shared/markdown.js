/**
 * Markdown rendering with syntax highlighting.
 * Uses marked.js and highlight.js from CDN with DOMPurify sanitization.
 */

import { escapeHtml } from './utils.js';

let _marked = null;
let _hljs = null;
let _DOMPurify = null;

/**
 * Check if markdown libraries are loaded.
 */
function checkLibraries() {
  if (typeof marked !== 'undefined') _marked = marked;
  if (typeof hljs !== 'undefined') _hljs = hljs;
  if (typeof DOMPurify !== 'undefined') _DOMPurify = DOMPurify;
}

/**
 * Parse markdown to HTML.
 */
export function parseMarkdown(markdown) {
  checkLibraries();

  if (!_marked?.parse) {
    // Fallback: escaped text with line breaks
    return escapeHtml(markdown || '').replace(/\n/g, '<br>');
  }

  const raw = _marked.parse(markdown || '');

  // Sanitize HTML to prevent XSS
  let safeHtml = raw;
  if (_DOMPurify?.sanitize) {
    safeHtml = _DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } });
  } else {
    // Fallback sanitization
    const temp = document.createElement('div');
    temp.innerHTML = raw;
    // Remove dangerous elements
    temp.querySelectorAll('script, style, iframe, object, embed, form, input').forEach((el) => el.remove());
    // Remove inline event handlers
    temp.querySelectorAll('[onclick],[onerror],[onload],[onmouseover],[onmouseenter],[onmouseleave]').forEach((el) => {
      [...el.attributes].forEach((attr) => {
        if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
      });
    });
    temp.querySelectorAll('a[href^="javascript:"]').forEach((el) => el.removeAttribute('href'));
    safeHtml = temp.innerHTML;
  }

  return safeHtml;
}

/**
 * Render markdown to a DOM element with syntax highlighting.
 * @param {string} markdown - Markdown text
 * @returns {Promise<HTMLElement>} - Wrapper element with rendered content
 */
export async function renderMarkdownToElement(markdown) {
  checkLibraries();

  const html = parseMarkdown(markdown);
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;

  // Apply syntax highlighting to code blocks
  if (_hljs) {
    wrapper.querySelectorAll('pre code').forEach((codeEl) => {
      try {
        _hljs.highlightElement(codeEl);
      } catch {
        // Unknown language, leave unhighlighted
      }

      // Wrap code block with header and copy button
      const pre = codeEl.parentElement;
      if (!pre || pre.classList.contains('code-block')) return;

      const langMatch = /language-(\w+)/.exec(codeEl.className || '');
      const lang = langMatch ? langMatch[1] : 'text';

      const block = document.createElement('div');
      block.className = 'code-block';
      block.innerHTML = `
        <div class="code-block-header">
          <span>${escapeHtml(lang)}</span>
          <button class="copy-code-btn" title="Copy code">
            <i class="fa-regular fa-copy"></i><span>Copy</span>
          </button>
        </div>
      `;

      pre.replaceWith(block);
      block.appendChild(pre);

      // Copy button handler
      block.querySelector('.copy-code-btn').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const codeText = codeEl.textContent;

        try {
          await navigator.clipboard.writeText(codeText);
          btn.classList.add('copied');
          btn.innerHTML = `<i class="fa-solid fa-check"></i><span>Copied</span>`;
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = `<i class="fa-regular fa-copy"></i><span>Copy</span>`;
          }, 1600);
        } catch {
          // Fallback: select text
          const range = document.createRange();
          range.selectNodeContents(codeEl);
          const sel = window.getSelection();
          sel?.removeAllRanges();
          sel?.addRange(range);
        }
      });
    });
  }

  return wrapper;
}

/**
 * Render markdown to HTML string (for message rendering).
 * @param {string} markdown - Markdown text
 * @returns {string} - HTML string
 */
export function renderMarkdown(markdown) {
  const temp = document.createElement('div');
  temp.innerHTML = parseMarkdown(markdown);

  // Apply syntax highlighting
  if (_hljs) {
    temp.querySelectorAll('pre code').forEach((codeEl) => {
      try {
        _hljs.highlightElement(codeEl);
      } catch {
        // ignore
      }

      const pre = codeEl.parentElement;
      if (pre && !pre.classList.contains('code-block')) {
        const langMatch = /language-(\w+)/.exec(codeEl.className || '');
        const lang = langMatch ? langMatch[1] : 'text';

        const block = document.createElement('div');
        block.className = 'code-block';
        block.innerHTML = `
          <div class="code-block-header">
            <span>${escapeHtml(lang)}</span>
            <button class="copy-code-btn"><i class="fa-regular fa-copy"></i><span>Copy</span></button>
          </div>
        `;
        pre.replaceWith(block);
        block.appendChild(pre);
      }
    });
  }

  return temp.innerHTML;
}

/**
 * Render markdown to string (lighter version for streaming).
 * Returns HTML with escaped content and placeholder for cursor.
 */
export function renderMarkdownStream(content) {
  const escaped = escapeHtml(content).replace(/\n/g, '<br>');
  // Wrap code blocks in markers for incremental highlighting
  return escaped;
}

/**
 * Set code theme dynamically.
 * @param {string} theme - Theme name (e.g., 'github-dark', 'atom-one-dark')
 */
export function setCodeTheme(theme) {
  const themeEl = $('#hljs-theme');
  const urls = {
    'github-dark': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css',
    'atom-one-dark': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css',
    'nord': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/nord.min.css',
    'dracula': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/dracula.min.css',
    'github': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css',
  };

  if (themeEl && urls[theme]) {
    themeEl.href = urls[theme];
    document.body.setAttribute('data-code-theme', theme);
  }
}

/**
 * Check if markdown libraries are available.
 */
export function areMarkdownLibsLoaded() {
  checkLibraries();
  return !!_marked && !!_hljs;
}