export {}; // ensure treated as module

declare global {
  interface Window {
    electronAPI: {
      openFiles: () => Promise<Array<{ filePath: string; buffer: string }>>;
    };
  }
}
