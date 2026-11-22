// 签名桥占位（签名在 JS 层时使用）。
// 契约：从 stdin 读一行 JSON 参数，输出一行 JSON 结果。
// 阶段 1/2 确认映客签名运行时后，按 douyin_python/node_env/sign_stripped.js 的方式补环境。
const readline = require('readline');

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

rl.on('line', (line) => {
  try {
    const params = JSON.parse(line);
    // TODO: 加载官方 SDK 并调用签名函数，返回 { ...params, sign: '...' }
    process.stdout.write(JSON.stringify(params) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ error: String(e) }) + '\n');
  }
});
