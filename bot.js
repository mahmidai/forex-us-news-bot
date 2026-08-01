import fetch from "node-fetch";

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHAT_ID = process.env.CHAT_ID;
const NEWS_URL = "https://www.forexfactory.com/news";

async function fetchNews() {
  const res = await fetch(NEWS_URL);
  const html = await res.text();

  const regex =
    /<a[^>]+href="(\/news\/[^"]+)"[^>]*>[\s\S]*?<span[^>]*class="title"[^>]*>(.*?)<\/span>/g;

  let match;
  let news = [];

  while ((match = regex.exec(html)) !== null) {
    const link = "https://www.forexfactory.com" + match[1];
    const title = match[2].trim();
    news.push({ title, link });
  }

  return news;
}

function isUSRelated(title) {
  const keywords = [
    "USD", "US ", "U.S.", "America", "American",
    "CPI", "PPI", "NFP", "GDP", "Inflation", "Jobs", "Unemployment",
    "Federal Reserve", "Fed", "FOMC",
    "Jerome Powell", "Powell",
    "Dow Jones", "DJIA", "S&P", "Nasdaq", "Wall Street",
    "Stocks", "Equities", "Market Selloff", "Market Rally",
    "Treasury"
  ];

  return keywords.some(k =>
    title.toLowerCase().includes(k.toLowerCase())
  );
}

async function sendToTelegram(text) {
  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;

  await fetch(url, {
    method: "POST",
    body: JSON.stringify({
      chat_id: CHAT_ID,
      text,
      parse_mode: "HTML"
    }),
    headers: { "Content-Type": "application/json" }
  });
}

async function runBot() {
  const news = await fetchNews();

  console.log("NEWS COUNT:", news.length);

  for (const item of news) {
    if (isUSRelated(item.title)) {
      const msg = `🇺🇸 <b>US / USD / Wall Street Related News</b>\n\n📢 <b>${item.title}</b>\n🔗 ${item.link}`;
      await sendToTelegram(msg);
    }
  }
}

runBot();
