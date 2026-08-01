import fetch from "node-fetch";
import { parseStringPromise } from "xml2js";

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHAT_ID = process.env.CHAT_ID;
const RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml";

async function fetchNews() {
  const res = await fetch(RSS_URL);
  let xml = await res.text();

  // پاک‌سازی کاراکترهای غیرمجاز XML
  xml = xml.replace(/&(?!amp;|lt;|gt;|quot;|apos;)/g, "&amp;");

  const data = await parseStringPromise(xml);

  const items = data.week.event;

  return items.map(item => ({
    title: item.title[0],
    country: item.country[0],
    link: "https://www.forexfactory.com" + item.url[0]
  }));
}

function isUSRelated(item) {
  return item.country === "USD" || item.country === "US";
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
    if (isUSRelated(item)) {
      const msg = `🇺🇸 <b>US / USD Related News</b>\n\n📢 <b>${item.title}</b>\n🔗 ${item.link}`;
      await sendToTelegram(msg);
    }
  }
}

runBot();
