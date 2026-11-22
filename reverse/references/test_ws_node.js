// 用 Node 24 内置 fetch + WebSocket 直连映客弹幕（仅学习研究）
const liveid = "1795004103423719";
const uid = "771687341";

async function main() {
  // 1) 拿在线房间
  let top = await fetch("https://webapi.busi.inke.cn/web/Live_top_pc").then(r => r.json());
  const room = top.data.list[0];
  const lid = room.live_id, u = room.uid;
  console.log("房间", lid, room.nick);

  // 2) 拿 WS URL
  const q = new URLSearchParams({roomid: lid, uid: u, id: lid, access_from: "pc_web"});
  let d = await fetch("https://chatroom.inke.cn/url?" + q, {
    headers: {Referer: "https://www.inke.cn/"}
  }).then(r => r.json());
  const wsUrl = d.url;
  console.log("WS", wsUrl.slice(0, 160));

  // 3) 连接
  const ws = new WebSocket(wsUrl, {headers: {Origin: "https://www.inke.cn"}});
  ws.onopen = () => console.log("OPEN");
  ws.onmessage = (e) => {
    try {
      const j = JSON.parse(e.data);
      if (j.b && j.b.ev === "s.m") {
        (j.ms || []).forEach(m => {
          if (m.tp === "pub") (m.statement_info || []).forEach(s => console.log("[弹幕]", s.c));
        });
      }
    } catch (err) {}
  };
  ws.onerror = (e) => console.log("WS ERROR", e.message || e.type);
  ws.onclose = (e) => console.log("CLOSE", e.code, e.reason);
  setTimeout(() => { ws.close(); process.exit(0); }, 25000);
}
main().catch(e => console.error("FATAL", e));
