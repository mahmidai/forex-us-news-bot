import fetch from "node-fetch";

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHAT_ID = process.env.CHAT_ID;
const API_URL = "https://cdn-nfs.fxfactory.com/_next/data/index.json";

async function fetchNews() {
  const res = await fetch(API_URL);
  const data = await res.json();

  const news = data.pageProps.news;

  return news.map(item => ({
    title: item.title,
    link: "https://www.forexfactory.com/news/" + item.id
  }));
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
