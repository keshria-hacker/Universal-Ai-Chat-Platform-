/**
 * Sidebar module - Chat history, new chat, sidebar collapse, mobile toggle.
 */

import { getApiBaseUrl, apiFetch, apiDelete } from '../../shared/http.js';
import { showToast } from '../../shared/toast.js';
import { escapeHtml, bucketFor } from '../../shared/utils.js';
import {
  getChats, setChats, getActiveChatId, setActiveChatId,
  getMessages, setMessages, getSelectedModel, selectModel,
  getAbortController, getModels, getSidebarCollapsed, setSidebarCollapsed
} from '../../core/state.js';
import { renderMessages, scrollToBottom, startNewChat } from '../chat/chat.js';

let elements = {};

/**
 * Initialize DOM references.
 */
export function initElements() {
  elements = {
    sidebar: $('#sidebar'),
    sidebarScrim: $('#sidebarScrim'),
    collapseSidebar: $('#collapseSidebar'),
    expandSidebar: $('#expandSidebar'),
    mobileSidebarToggle: $('#mobileSidebarToggle'),
    newChatBtn: $('#newChatBtn'),
    mobileNewChat: $('#mobileNewChat'),
    searchChats: $('#searchChats'),
    chatHistory: $('#chatHistory'),
  };
}

/**
 * Open mobile sidebar.
 */
export function openMobileSidebar() {
  elements.sidebar?.classList.add('mobile-open');
  elements.sidebarScrim?.classList.add('show');
}

/**
 * Close mobile sidebar.
 */
export function closeMobileSidebar() {
  elements.sidebar?.classList.remove('mobile-open');
  elements.sidebarScrim?.classList.remove('show');
}

/**
 * Toggle sidebar collapse state.
 */
export function toggleSidebarCollapse() {
  const next = !getSidebarCollapsed();
  setSidebarCollapsed(next);
  elements.sidebar?.classList.toggle('collapsed', next);
  elements.expandSidebar?.classList.toggle('hidden', !next);
}

/**
 * Load chat list from backend.
 */
export async function loadChatList() {
  try {
    const res = await apiFetch('/chats');
    const chats = await res.json();
    setChats(chats);
    renderChatHistory(elements.searchChats?.value || '');
  } catch (err) {
    showToast({ type: 'error', title: 'Could not load chat history', message: err.message });
  }
}

/**
 * Render chat history with date bucketing and search filter.
 */
export function renderChatHistory(filter = '') {
  const q = filter.trim().toLowerCase();
  const buckets = ['Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days', 'Older'];
  const container = elements.chatHistory;
  if (!container) return;

  container.innerHTML = '';
  let anyMatch = false;

  buckets.forEach((bucket) => {
    const items = getChats().filter((c) => bucketFor(c.updated_at) === bucket && c.title.toLowerCase().includes(q));
    if (!items.length) return;
    anyMatch = true;

    const label = document.createElement('div');
    label.className = 'chat-history-label';
    label.textContent = bucket;
    container.appendChild(label);

    items.forEach((chat) => {
      const item = document.createElement('div');
      item.className = 'chat-item' + (chat.id === getActiveChatId() ? ' active' : '');
      item.dataset.chatId = chat.id;
      item.innerHTML = `
        <i class="fa-regular fa-message chat-icon"></i>
        <span>${escapeHtml(chat.title)}</span>
        <button class="icon-btn chat-item-menu" title="Delete chat" aria-label="Delete chat"><i class="fa-solid fa-trash"></i></button>
      `;
      item.addEventListener('click', (e) => {
        if (e.target.closest('.chat-item-menu')) {
          e.stopPropagation();
          deleteChat(chat.id);
          return;
        }
        openChat(chat.id);
        if (window.innerWidth <= 900) closeMobileSidebar();
      });
      container.appendChild(item);
    });
  });

  if (!anyMatch) {
    const empty = document.createElement('div');
    empty.className = 'no-results';
    empty.textContent = getChats().length ? `No chats match "${filter}"` : 'No conversations yet — start one below.';
    container.appendChild(empty);
  }
}

/**
 * Open a chat by ID.
 */
export async function openChat(chatId) {
  setActiveChatId(chatId);
  renderChatHistory(elements.searchChats?.value || '');

  $('#welcomeScreen')?.classList.add('hidden');
  $('#messages')?.classList.add('hidden');
  $('#errorState')?.classList.add('hidden');
  $('#skeletonWrap')?.classList.remove('hidden');

  try {
    const res = await apiFetch(`/chats/${chatId}`);
    const chat = await res.json();

    // Select the model used in this chat
    const allModels = getModels();
    if (allModels) {
      const model = allModels.find((m) => m.id === chat.model);
      if (model) selectModel(model, { silent: true });
    }

    setMessages(chat.messages);
    $('#skeletonWrap')?.classList.add('hidden');
    $('#messages')?.classList.remove('hidden');
    renderMessages();
    scrollToBottom(false);
  } catch (err) {
    $('#skeletonWrap')?.classList.add('hidden');
    $('#errorState')?.classList.remove('hidden');
    $('#errorState').querySelector('strong').textContent = 'Could not load this conversation.';
    $('#errorState').querySelector('p').textContent = err.message;
  }
}

/**
 * Delete chat confirmation and handler.
 */
let pendingDeleteChatId = null;

function showConfirmDelete(chatId) {
  pendingDeleteChatId = chatId;
  $('#confirmTitle').textContent = 'Delete chat?';
  $('#confirmMessage').textContent = 'This conversation will be permanently removed.';
  $('#confirmOverlay').classList.remove('hidden');
  updateBodyScrollLock();
  setTimeout(() => $('#confirmCancel').focus(), 50);
}

function hideConfirm() {
  $('#confirmOverlay').classList.add('hidden');
  pendingDeleteChatId = null;
  updateBodyScrollLock();
}

export function deleteChat(chatId) {
  showConfirmDelete(chatId);
}

/**
 * Initialize sidebar event listeners.
 */
export function initSidebar() {
  initElements();

  elements.newChatBtn?.addEventListener('click', startNewChat);
  elements.mobileNewChat?.addEventListener('click', () => { startNewChat(); closeMobileSidebar(); });
  elements.collapseSidebar?.addEventListener('click', toggleSidebarCollapse);
  elements.expandSidebar?.addEventListener('click', toggleSidebarCollapse);
  elements.mobileSidebarToggle?.addEventListener('click', openMobileSidebar);
  elements.sidebarScrim?.addEventListener('click', closeMobileSidebar);
  elements.searchChats?.addEventListener('input', () => renderChatHistory(elements.searchChats.value));

  // Confirm dialog event listeners
  $('#confirmCancel')?.addEventListener('click', hideConfirm);
  $('#confirmOverlay')?.addEventListener('click', (e) => { if (e.target === $('#confirmOverlay')) hideConfirm(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#confirmOverlay')?.classList.contains('hidden')) hideConfirm(); });
  $('#confirmDelete')?.addEventListener('click', async () => {
    const chatId = pendingDeleteChatId;
    hideConfirm();
    if (!chatId) return;
    try {
      await apiFetch(`/chats/${chatId}`, { method: 'DELETE' });
      setChats(getChats().filter((c) => c.id !== chatId));
      if (getActiveChatId() === chatId) startNewChat();
      renderChatHistory(elements.searchChats?.value || '');
      showToast({ type: 'success', message: 'Chat deleted.' });
    } catch (err) {
      showToast({ type: 'error', title: 'Could not delete chat', message: err.message });
    }
  });
}

/**
 * Lock/unlock body scroll.
 */
export function updateBodyScrollLock() {
  // Check if any overlay is open
  const anyOpen = !$('#settingsOverlay')?.classList.contains('hidden') ||
                  !$('#confirmOverlay')?.classList.contains('hidden') ||
                  !document.getElementById('skillsOverlay')?.classList.contains('hidden');
  document.body.style.overflow = anyOpen ? 'hidden' : '';
}
