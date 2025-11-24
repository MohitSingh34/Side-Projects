// mock-ws-server.js - very small test server for frontend prototype
const WebSocket = require("ws");
const wss = new WebSocket.Server({ port: 4000 });
console.log("Mock WS server running on ws://localhost:4000");

function broadcast(msg) {
  const s = JSON.stringify(msg);
  wss.clients.forEach((c) => {
    if (c.readyState === WebSocket.OPEN) c.send(s);
  });
}

wss.on("connection", function connection(ws) {
  console.log("client connected");
  ws.on("message", function incoming(data) {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === "authenticate") {
        // accept any token for prototype
        ws.send(
          JSON.stringify({
            type: "authSuccess",
            message: "Authenticated (mock)",
          })
        );
        // after auth, send a couple of sample users coming online
        setTimeout(() => {
          broadcast({
            type: "userConnected",
            userId: "user-1",
            username: "Deepseek",
            avatarUrl: "https://i.pravatar.cc/40?u=1",
            timestamp: new Date().toISOString(),
          });
          broadcast({
            type: "userConnected",
            userId: "user-2",
            username: "Gemini",
            avatarUrl: "https://i.pravatar.cc/40?u=2",
            timestamp: new Date().toISOString(),
          });
        }, 600);
        // and periodically send location updates for those users
        let t = 0;
        const interval = setInterval(() => {
          t++;
          broadcast({
            type: "userLocationUpdate",
            userId: "user-1",
            username: "Deepseek",
            lat: 19.07 + Math.sin(t / 5) * 0.001,
            lng: 72.87 + Math.cos(t / 5) * 0.001,
            timestamp: new Date().toISOString(),
          });
          broadcast({
            type: "userLocationUpdate",
            userId: "user-2",
            username: "Gemini",
            lat: 28.7 + Math.cos(t / 7) * 0.0009,
            lng: 77.1 + Math.sin(t / 7) * 0.0009,
            timestamp: new Date().toISOString(),
          });
          // after some cycles, disconnect one user
          if (t === 25) {
            broadcast({
              type: "userDisconnected",
              userId: "user-2",
              timestamp: new Date().toISOString(),
            });
          }
        }, 1200);

        ws.on("close", () => clearInterval(interval));
      } else {
        // echo or ignore other messages (startTracking/locationUpdate) for prototype
        // optionally broadcast client's locationUpdate back to others to simulate server relay
        if (msg.type === "locationUpdate" && msg.deviceId) {
          broadcast({
            type: "userLocationUpdate",
            userId: "you",
            username: "You",
            lat: msg.lat,
            lng: msg.lng,
            timestamp: new Date().toISOString(),
          });
        }
      }
    } catch (e) {
      console.warn("invalid msg", e);
    }
  });
});
