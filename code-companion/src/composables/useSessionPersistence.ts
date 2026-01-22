import { ref, onMounted, onUnmounted } from 'vue';
import { Message, Session, ContextItem } from '@/types';
import {
  saveSession,
  getSession,
  getSessions,
  saveMessages,
  getMessages,
  saveCheckpoint,
  getCheckpoint,
  deleteCheckpoint,
  isOnline,
  onOnlineStatusChange,
  SessionCheckpoint,
  saveContextItems,
  getContextItems,
  addContextItem as addContextItemToStorage,
  removeContextItem as removeContextItemFromStorage,
  updateContextItem as updateContextItemInStorage,
} from '@/lib/sessionStorage';

interface UseSessionPersistenceOptions {
  sessionId: string;
  onResumeAvailable?: (checkpoint: SessionCheckpoint) => void;
}

export const useSessionPersistence = ({ sessionId, onResumeAvailable }: UseSessionPersistenceOptions) => {
  const session = ref<Session | null>(null);
  const messages = ref<Message[]>([]);
  const contextItems = ref<ContextItem[]>([]);
  const online = ref(isOnline());
  const checkpoint = ref<SessionCheckpoint | null>(null);
  const initialized = ref(false);

  // Load session, messages, and context items on mount
  onMounted(() => {
    const loadedSession = getSession(sessionId);
    const loadedMessages = getMessages(sessionId);
    const loadedCheckpoint = getCheckpoint(sessionId);
    const loadedContextItems = getContextItems(sessionId);

    if (loadedSession) {
      session.value = loadedSession;
    }

    if (loadedMessages.length > 0) {
      messages.value = loadedMessages;
    }

    if (loadedContextItems.length > 0) {
      contextItems.value = loadedContextItems;
    }

    if (loadedCheckpoint && loadedCheckpoint.status === 'interrupted') {
      checkpoint.value = loadedCheckpoint;
      onResumeAvailable?.(loadedCheckpoint);
    }

    initialized.value = true;
  });

  // Listen for online/offline changes
  const unsubscribe = onOnlineStatusChange((isOnlineStatus) => {
    online.value = isOnlineStatus;
  });

  onUnmounted(() => {
    unsubscribe();
  });

  // Update session
  const updateSession = (updates: Partial<Session>) => {
    if (!session.value) return;
    const updated = { ...session.value, ...updates, updatedAt: new Date() };
    saveSession(updated);
    session.value = updated;
  };

  // Add message
  const addMessage = (message: Message) => {
    const updated = [...messages.value, message];
    saveMessages(sessionId, updated);
    messages.value = updated;
  };

  // Update last message (for streaming)
  const updateLastMessage = (content: string, isStreaming = true) => {
    if (messages.value.length === 0) return;
    const updated = [...messages.value];
    const lastIndex = updated.length - 1;
    updated[lastIndex] = {
      ...updated[lastIndex],
      content,
      isStreaming,
    };
    saveMessages(sessionId, updated);
    messages.value = updated;
  };

  // Create checkpoint for resumption
  const createCheckpoint = (streamingContent: string, position: number) => {
    const lastMessage = messages.value[messages.value.length - 1];
    if (!lastMessage) return;

    const cp: SessionCheckpoint = {
      sessionId,
      lastMessageId: lastMessage.id,
      streamingContent,
      position,
      timestamp: Date.now(),
      status: 'interrupted',
    };

    saveCheckpoint(cp);
    checkpoint.value = cp;
  };

  // Clear checkpoint after successful completion
  const clearCheckpoint = () => {
    deleteCheckpoint(sessionId);
    checkpoint.value = null;
  };

  // Get all sessions for session list
  const getAllSessions = () => {
    return getSessions();
  };

  // Add context item
  const addContextItem = (item: ContextItem) => {
    const existingIndex = contextItems.value.findIndex(i => i.id === item.id);
    let updated: ContextItem[];
    if (existingIndex >= 0) {
      updated = [...contextItems.value];
      updated[existingIndex] = { ...updated[existingIndex], ...item, lastAccessed: new Date() };
    } else {
      updated = [...contextItems.value, item];
    }
    saveContextItems(sessionId, updated);
    contextItems.value = updated;
    addContextItemToStorage(sessionId, item);
  };

  // Remove context item
  const removeContextItem = (itemId: string) => {
    const updated = contextItems.value.filter(i => i.id !== itemId);
    saveContextItems(sessionId, updated);
    contextItems.value = updated;
    removeContextItemFromStorage(sessionId, itemId);
  };

  // Update context item
  const updateContextItem = (itemId: string, updates: Partial<ContextItem>) => {
    const updated = contextItems.value.map(item =>
      item.id === itemId ? { ...item, ...updates } : item
    );
    saveContextItems(sessionId, updated);
    contextItems.value = updated;
    updateContextItemInStorage(sessionId, itemId, updates);
  };

  // Toggle pin status
  const togglePinContextItem = (itemId: string) => {
    const item = contextItems.value.find(i => i.id === itemId);
    if (!item) return;
    const updated = contextItems.value.map(i =>
      i.id === itemId ? { ...i, pinned: !i.pinned } : i
    );
    saveContextItems(sessionId, updated);
    contextItems.value = updated;
    updateContextItemInStorage(sessionId, itemId, { pinned: !item.pinned });
  };

  // Clear unpinned items
  const clearUnpinnedItems = () => {
    const updated = contextItems.value.filter(item => item.pinned);
    saveContextItems(sessionId, updated);
    contextItems.value = updated;
  };

  // Set all context items (for compression)
  const setAllContextItems = (items: ContextItem[]) => {
    contextItems.value = items;
    saveContextItems(sessionId, items);
  };

  return {
    session,
    messages,
    contextItems,
    online,
    checkpoint,
    initialized,
    updateSession,
    addMessage,
    updateLastMessage,
    createCheckpoint,
    clearCheckpoint,
    getAllSessions,
    addContextItem,
    removeContextItem,
    updateContextItem,
    togglePinContextItem,
    clearUnpinnedItems,
    setAllContextItems,
  };
};
