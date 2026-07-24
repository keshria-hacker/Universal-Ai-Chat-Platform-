/**
 * Documents feature - File upload and extraction.
 * Note: File upload is handled in chat.js, this module handles the document
 * extraction preview and document list if needed.
 */

import { getApiBaseUrl, apiFetch, apiPostForm } from '../../shared/http.js';
import { showToast } from '../../shared/toast.js';
import { escapeHtml, formatBytes, extOf, getFileInfo } from '../../shared/utils.js';

/**
 * Handle file selection for document extraction (standalone, not in chat).
 * This can be used for a dedicated documents page if needed.
 */
export async function extractDocument(file) {
  const ext = extOf(file.name);
  const form = new FormData();
  form.append('file', file);

  try {
    const res = await apiFetch('/files', { method: 'POST', body: form });
    const data = await res.json();
    // Return file_id for the extracted document
    return { fileId: data.file_id, size: data.size_bytes };
  } catch (err) {
    showToast({ type: 'error', title: `Failed to process ${file.name}`, message: err.message });
    throw err;
  }
}

/**
 * Get extracted text content for a file.
 */
export async function getDocumentPreview(fileId) {
  try {
    const res = await apiFetch(`/files/${fileId}/preview`);
    return await res.json();
  } catch (err) {
    showToast({ type: 'error', title: 'Could not preview document', message: err.message });
    throw err;
  }
}

/**
 * List all uploaded documents.
 */
export async function listDocuments() {
  try {
    const res = await apiFetch('/files');
    return await res.json();
  } catch (err) {
    showToast({ type: 'error', title: 'Could not list documents', message: err.message });
    return [];
  }
}

/**
 * Delete a document.
 */
export async function deleteDocument(fileId) {
  try {
    await apiFetch(`/files/${fileId}`, { method: 'DELETE' });
    showToast({ type: 'success', message: 'Document deleted.' });
  } catch (err) {
    showToast({ type: 'error', title: 'Could not delete document', message: err.message });
    throw err;
  }
}

export { showToast, formatBytes, extOf, getFileInfo, escapeHtml };