// mock-ws-server.js
const WebSocket = require("ws");
const wss = new WebSocket.Server({ port: 4000 });
console.log("✅ Mock WS server running on ws://localhost:4000");

function broadcast(msg) {
  const s = JSON.stringify(msg);
  wss.clients.forEach((c) => {
    if (c.readyState === WebSocket.OPEN) c.send(s);
  });
}

wss.on("connection", (ws) => {
  console.log("client connected");
  ws.on("message", (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === "authenticate") {
        ws.send(
          JSON.stringify({
            type: "authSuccess",
            message: "Authenticated (mock)",
          })
        );

        setTimeout(() => {
          broadcast({
            type: "userConnected",
            userId: "user-1",
            username: "Deepseek",
            avatarUrl: "https://i.pravatar.cc/40?u=1",
            timestamp: new Date().toISOString(),
          });
        }, 600);
      }
    } catch (e) {
      console.warn("invalid msg", e);
    }
  });
});
