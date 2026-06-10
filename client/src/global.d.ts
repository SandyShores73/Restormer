export {};

declare global {
  interface Window {
    phoneAgentDesktop?: {
      platform: string;
    };
  }
}
