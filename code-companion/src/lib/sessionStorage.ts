import { Message, Session, ContextItem } from '@/types';

const STORAGE_KEY = 'anycode_sessions';
const MESSAGES_KEY = 'anycode_messages';
const CHECKPOINT_KEY = 'anycode_checkpoints';
const CONTEXT_ITEMS_KEY = 'anycode_context_items';

export interface SessionCheckpoint {
  sessionId: string;
  lastMessageId: string;
  streamingContent: string;
  position: number;
  timestamp: number;
  status: 'interrupted' | 'completed';
}

export interface StoredSession extends Session {
  messages: Message[];
}

// Session Storage
export const saveSession = (session: Session): void => {
  try {
    const sessions = getSessions();
    const index = sessions.findIndex(s => s.id === session.id);
    if (index >= 0) {
      sessions[index] = session;
    } else {
      sessions.unshift(session);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (error) {
    console.error('Failed to save session:', error);
  }
};

export const getSessions = (): Session[] => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return [];
    const sessions = JSON.parse(data);
    return sessions.map((s: Session) => ({
      ...s,
      createdAt: new Date(s.createdAt),
      updatedAt: new Date(s.updatedAt),
    }));
  } catch (error) {
    console.error('Failed to get sessions:', error);
    return [];
  }
};

export const getSession = (sessionId: string): Session | null => {
  const sessions = getSessions();
  return sessions.find(s => s.id === sessionId) || null;
};

export const deleteSession = (sessionId: string): void => {
  try {
    const sessions = getSessions().filter(s => s.id !== sessionId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    deleteMessages(sessionId);
    deleteCheckpoint(sessionId);
  } catch (error) {
    console.error('Failed to delete session:', error);
  }
};

// Message Storage
export const saveMessages = (sessionId: string, messages: Message[]): void => {
  try {
    const allMessages = getAllMessages();
    allMessages[sessionId] = messages;
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(allMessages));
  } catch (error) {
    console.error('Failed to save messages:', error);
  }
};

export const getMessages = (sessionId: string): Message[] => {
  try {
    const allMessages = getAllMessages();
    const messages = allMessages[sessionId] || [];
    return messages.map((m: Message) => ({
      ...m,
      timestamp: new Date(m.timestamp),
    }));
  } catch (error) {
    console.error('Failed to get messages:', error);
    return [];
  }
};

const getAllMessages = (): Record<string, Message[]> => {
  try {
    const data = localStorage.getItem(MESSAGES_KEY);
    return data ? JSON.parse(data) : {};
  } catch {
    return {};
  }
};

const deleteMessages = (sessionId: string): void => {
  try {
    const allMessages = getAllMessages();
    delete allMessages[sessionId];
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(allMessages));
  } catch (error) {
    console.error('Failed to delete messages:', error);
  }
};

// Checkpoint Storage (for resumption)
export const saveCheckpoint = (checkpoint: SessionCheckpoint): void => {
  try {
    const checkpoints = getCheckpoints();
    checkpoints[checkpoint.sessionId] = checkpoint;
    localStorage.setItem(CHECKPOINT_KEY, JSON.stringify(checkpoints));
  } catch (error) {
    console.error('Failed to save checkpoint:', error);
  }
};

export const getCheckpoint = (sessionId: string): SessionCheckpoint | null => {
  const checkpoints = getCheckpoints();
  return checkpoints[sessionId] || null;
};

export const deleteCheckpoint = (sessionId: string): void => {
  try {
    const checkpoints = getCheckpoints();
    delete checkpoints[sessionId];
    localStorage.setItem(CHECKPOINT_KEY, JSON.stringify(checkpoints));
  } catch (error) {
    console.error('Failed to delete checkpoint:', error);
  }
};

const getCheckpoints = (): Record<string, SessionCheckpoint> => {
  try {
    const data = localStorage.getItem(CHECKPOINT_KEY);
    return data ? JSON.parse(data) : {};
  } catch {
    return {};
  }
};

// Online/Offline Detection
export const isOnline = (): boolean => navigator.onLine;

export const onOnlineStatusChange = (callback: (online: boolean) => void): () => void => {
  const handleOnline = () => callback(true);
  const handleOffline = () => callback(false);
  
  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);
  
  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
};

// Context Items Storage
const getAllContextItems = (): Record<string, ContextItem[]> => {
  try {
    const data = localStorage.getItem(CONTEXT_ITEMS_KEY);
    if (!data) return {};
    const allItems = JSON.parse(data);
    // Convert dates
    Object.keys(allItems).forEach(sessionId => {
      allItems[sessionId] = allItems[sessionId].map((item: ContextItem) => ({
        ...item,
        addedAt: new Date(item.addedAt),
        lastAccessed: item.lastAccessed ? new Date(item.lastAccessed) : undefined,
      }));
    });
    return allItems;
  } catch {
    return {};
  }
};

export const saveContextItems = (sessionId: string, items: ContextItem[]): void => {
  try {
    const allItems = getAllContextItems();
    allItems[sessionId] = items;
    localStorage.setItem(CONTEXT_ITEMS_KEY, JSON.stringify(allItems));
  } catch (error) {
    console.error('Failed to save context items:', error);
  }
};

export const getContextItems = (sessionId: string): ContextItem[] => {
  const allItems = getAllContextItems();
  return allItems[sessionId] || [];
};

export const addContextItem = (sessionId: string, item: ContextItem): void => {
  const items = getContextItems(sessionId);
  // Check if item already exists
  const existingIndex = items.findIndex(i => i.id === item.id);
  if (existingIndex >= 0) {
    items[existingIndex] = { ...items[existingIndex], ...item, lastAccessed: new Date() };
  } else {
    items.push(item);
  }
  saveContextItems(sessionId, items);
};

export const removeContextItem = (sessionId: string, itemId: string): void => {
  const items = getContextItems(sessionId).filter(i => i.id !== itemId);
  saveContextItems(sessionId, items);
};

export const updateContextItem = (
  sessionId: string, 
  itemId: string, 
  updates: Partial<ContextItem>
): void => {
  const items = getContextItems(sessionId);
  const index = items.findIndex(i => i.id === itemId);
  if (index >= 0) {
    items[index] = { ...items[index], ...updates };
    saveContextItems(sessionId, items);
  }
};

export const deleteContextItems = (sessionId: string): void => {
  try {
    const allItems = getAllContextItems();
    delete allItems[sessionId];
    localStorage.setItem(CONTEXT_ITEMS_KEY, JSON.stringify(allItems));
  } catch (error) {
    console.error('Failed to delete context items:', error);
  }
};
