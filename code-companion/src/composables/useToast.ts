export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
  duration?: number;
}

export function useToast() {
  const toast = (options: {
    title: string;
    description?: string;
    variant?: 'default' | 'destructive';
    duration?: number;
  }) => {
    // Simple toast implementation - can be enhanced with a toast library later
    console.log(`[Toast] ${options.title}${options.description ? `: ${options.description}` : ''}`);
    // For now, just log to console. Can integrate sonner or another toast library later
  };

  return {
    toast,
  };
}
