/**
 * Shared DOM utilities.
 * Encapsulates common DOM operations for consistency.
 */

/**
 * Safe querySelector with optional context.
 */
export function $(selector, context = document) {
  return context.querySelector(selector);
}

/**
 * Safe querySelectorAll with optional context.
 */
export function $$(selector, context = document) {
  return Array.from(context.querySelectorAll(selector));
}

/**
 * Create an element with attributes and children.
 * @param {string} tag - Element tag name
 * @param {Object} attrs - Attributes to set
 * @param {Array|string|Node} children - Child nodes or HTML string
 * @returns {HTMLElement}
 */
export function createEl(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === 'class') {
      el.className = value;
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(el.style, value);
    } else if (key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'dataset' && typeof value === 'object') {
      Object.entries(value).forEach(([k, v]) => { el.dataset[k] = v; });
    } else {
      el.setAttribute(key, value);
    }
  });

  if (typeof children === 'string') {
    el.innerHTML = children;
  } else if (Array.isArray(children)) {
    children.forEach((child) => {
      if (child instanceof Node) {
        el.appendChild(child);
      } else if (typeof child === 'string') {
        el.insertAdjacentHTML('beforeend', child);
      }
    });
  }
  return el;
}

/**
 * Remove all children from an element.
 */
export function empty(el) {
  if (!el) return;
  while (el.firstChild) {
    el.removeChild(el.firstChild);
  }
}

/**
 * Toggle class on element.
 */
export function toggleClass(el, className, force) {
  if (!el) return;
  el.classList.toggle(className, force);
}

/**
 * Add class if not present.
 */
export function addClass(el, className) {
  if (!el) return;
  el.classList.add(className);
}

/**
 * Remove class if present.
 */
export function removeClass(el, className) {
  if (!el) return;
  el.classList.remove(className);
}

/**
 * Check if element has class.
 */
export function hasClass(el, className) {
  return el?.classList.contains(className) ?? false;
}

/**
 * Set multiple attributes at once.
 */
export function setAttrs(el, attrs) {
  if (!el) return;
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      el.removeAttribute(key);
    } else {
      el.setAttribute(key, value);
    }
  });
}

/**
 * Get data attribute value.
 */
export function getData(el, key) {
  return el?.dataset[key];
}

/**
 * Set data attribute.
 */
export function setData(el, key, value) {
  if (!el) return;
  el.dataset[key] = value;
}

/**
 * Lock/unlock body scroll (for modals).
 */
let _scrollLockCount = 0;
export function lockBodyScroll() {
  _scrollLockCount++;
  if (_scrollLockCount === 1) {
    document.body.style.overflow = 'hidden';
  }
}

export function unlockBodyScroll() {
  _scrollLockCount = Math.max(0, _scrollLockCount - 1);
  if (_scrollLockCount === 0) {
    document.body.style.overflow = '';
  }
}

/**
 * Trap focus within an element (for modal accessibility).
 * @param {HTMLElement} container - Element to trap focus in
 * @returns {Function} Cleanup function to remove trap
 */
export function trapFocus(container) {
  if (!container) return () => {};

  const focusableSelectors = [
    'button:not([disabled])',
    '[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"]):not([disabled])',
  ].join(', ');

  const getFocusable = () => Array.from(container.querySelectorAll(focusableSelectors))
    .filter((el) => el.offsetParent !== null);

  function handleKeyDown(e) {
    if (e.key !== 'Tab') return;
    const focusable = getFocusable();
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  container.addEventListener('keydown', handleKeyDown);
  const focusable = getFocusable();
  if (focusable.length) focusable[0].focus();

  return () => {
    container.removeEventListener('keydown', handleKeyDown);
  };
}

/**
 * Show/hide element with display property.
 */
export function show(el, display = '') {
  if (!el) return;
  el.style.display = display || (el.tagName === 'TR' ? 'table-row' : el.tagName === 'TD' ? 'table-cell' : '');
  el.classList.remove('hidden');
}

export function hide(el) {
  if (!el) return;
  el.style.display = 'none';
  el.classList.add('hidden');
}

/**
 * Toggle element visibility.
 */
export function toggle(el, force) {
  if (!el) return;
  const hidden = el.classList.contains('hidden');
  if (force === undefined) force = hidden;
  if (force) show(el); else hide(el);
}

/**
 * Debounce helper for DOM events.
 */
export function debounce(fn, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      fn(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}