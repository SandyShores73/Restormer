export {}; // ensure treated as module

declare global {
  interface Window {
    electronAPI: {
      openFile: () => Promise<{ filePath: string; buffer: string } | null>;
    };
  }
}
