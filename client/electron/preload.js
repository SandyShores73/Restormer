const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("phoneAgentDesktop", {
  platform: process.platform
});
