import { ContextItem } from '@/types';
import { CompressionStrategy, CompressionOptions } from '@/components/chat/ContextCompressionDialog';

export interface CompressionResult {
  removedItems: ContextItem[];
  remainingItems: ContextItem[];
  savedTokens: number;
}

export const compressContext = (
  items: ContextItem[],
  strategy: CompressionStrategy,
  options?: CompressionOptions
): CompressionResult => {
  let remainingItems: ContextItem[] = [];
  let removedItems: ContextItem[] = [];

  switch (strategy) {
    case 'smart': {
      // Smart compression: Keep pinned, prioritize by priority and recency
      const pinnedItems = items.filter(item => item.pinned);
      const unpinnedItems = items.filter(item => !item.pinned);
      
      // Sort by priority (higher first) and recency
      const sortedUnpinned = [...unpinnedItems].sort((a, b) => {
        if (a.priority !== b.priority) return b.priority - a.priority;
        return new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime();
      });

      // Keep top 60% of unpinned items by token count
      const totalUnpinnedTokens = unpinnedItems.reduce((sum, item) => sum + item.tokens, 0);
      const targetTokens = totalUnpinnedTokens * 0.6;
      
      let currentTokens = 0;
      const keptUnpinned: ContextItem[] = [];
      const removedUnpinned: ContextItem[] = [];

      for (const item of sortedUnpinned) {
        if (currentTokens + item.tokens <= targetTokens) {
          keptUnpinned.push(item);
          currentTokens += item.tokens;
        } else {
          removedUnpinned.push(item);
        }
      }

      remainingItems = [...pinnedItems, ...keptUnpinned];
      removedItems = removedUnpinned;
      break;
    }

    case 'remove-old': {
      const keepCount = options?.keepRecentCount || 10;
      const historyItems = items.filter(item => item.type === 'history');
      const nonHistoryItems = items.filter(item => item.type !== 'history');
      
      // Sort by addedAt descending (newest first)
      const sortedHistory = [...historyItems].sort(
        (a, b) => new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime()
      );

      const keptHistory = sortedHistory.slice(0, keepCount);
      const removedHistory = sortedHistory.slice(keepCount);

      remainingItems = [...nonHistoryItems, ...keptHistory];
      removedItems = removedHistory;
      break;
    }

    case 'remove-unpinned': {
      remainingItems = items.filter(item => item.pinned);
      removedItems = items.filter(item => !item.pinned);
      break;
    }

    case 'custom': {
      const targetTokens = options?.targetTokens || 0;
      const pinnedItems = items.filter(item => item.pinned);
      const unpinnedItems = items.filter(item => !item.pinned);
      
      const pinnedTokens = pinnedItems.reduce((sum, item) => sum + item.tokens, 0);
      
      // If pinned items already exceed target, keep only pinned
      if (pinnedTokens >= targetTokens) {
        remainingItems = pinnedItems;
        removedItems = unpinnedItems;
      } else {
        // Fill remaining budget with highest priority unpinned items
        const remainingBudget = targetTokens - pinnedTokens;
        const sortedUnpinned = [...unpinnedItems].sort((a, b) => b.priority - a.priority);
        
        let currentTokens = 0;
        const keptUnpinned: ContextItem[] = [];
        const removedUnpinned: ContextItem[] = [];

        for (const item of sortedUnpinned) {
          if (currentTokens + item.tokens <= remainingBudget) {
            keptUnpinned.push(item);
            currentTokens += item.tokens;
          } else {
            removedUnpinned.push(item);
          }
        }

        remainingItems = [...pinnedItems, ...keptUnpinned];
        removedItems = removedUnpinned;
      }
      break;
    }
  }

  const savedTokens = removedItems.reduce((sum, item) => sum + item.tokens, 0);

  return {
    removedItems,
    remainingItems,
    savedTokens,
  };
};
