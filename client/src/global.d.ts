export {}; // ensure treated as module

declare global {
  interface Window {
    electronAPI: {
      openFiles: () => Promise<Array<{ filePath: string; buffer: string }>>;
    };
    __LUMA_DEBUG__?: unknown;
  }
}

declare module "*.svg" {
  const content: string;
  export default content;
}
