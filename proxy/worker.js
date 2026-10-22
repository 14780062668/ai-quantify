// Cloudflare Worker：体彩接口中转代理
// 部署后得到 https://xxx.workers.dev/?url=<目标URL> 的转发服务
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = url.searchParams.get("url");
    // 只允许转发体彩接口，防止被滥用
    if (!target || !target.startsWith("https://webapi.sporttery.cn/")) {
      return new Response("forbidden", { status: 403 });
    }
    try {
      const resp = await fetch(target, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          Referer: "https://www.sporttery.cn/",
          Origin: "https://www.sporttery.cn",
          Accept: "application/json, text/plain, */*",
          "Accept-Language": "zh-CN,zh;q=0.9",
        },
      });
      const body = await resp.text();
      return new Response(body, {
        status: resp.status,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
        },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e) }), { status: 502 });
    }
  },
};
