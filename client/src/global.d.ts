export {}; // ensure treated as module

declare global {
  interface Window {
    electronAPI: {
      openFiles: () => Promise<Array<{ filePath: string; buffer: string }>>;
    };
    __LUMA_DEBUG__?: unknown;
  }

  interface ImportMetaEnv {
    readonly VITE_API_BASE?: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

declare module "*.svg" {
  const content: string;
  export default content;
}
