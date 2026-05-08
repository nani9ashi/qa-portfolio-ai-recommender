/**
 * Express サーバ起動エントリポイント
 *
 * 役割:
 *   - .env から ANTHROPIC_API_KEY 等を読み込む
 *   - フロントエンド (http://localhost:5173) からの CORS を許可
 *   - /api/recommend ルートをマウント
 *   - ポート 3001 で待ち受け
 */

require("dotenv").config({ path: __dirname + "/.env" });

const express = require("express");
const cors = require("cors");
const recommendRouter = require("./routes/recommend");

const app = express();
const PORT = process.env.PORT || 3001;
const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || "http://localhost:5173";

// 起動時のキー存在チェック (警告のみ、サーバ起動は止めない)
if (!process.env.ANTHROPIC_API_KEY) {
  console.warn(
    "[起動警告] ANTHROPIC_API_KEY が設定されていません。" +
    " backend/.env に ANTHROPIC_API_KEY を設定してください。" +
    " /api/recommend は 500 を返します。"
  );
}

app.use(cors({ origin: FRONTEND_ORIGIN }));
app.use(express.json());

// ヘルスチェック (動作確認用)
app.get("/health", (req, res) => {
  res.json({ status: "ok", model: process.env.CLAUDE_MODEL || "default", ts: new Date().toISOString() });
});

// レコメンド本体
app.use("/api", recommendRouter);

app.listen(PORT, () => {
  console.log(`[backend] Listening on http://localhost:${PORT}`);
  console.log(`[backend] CORS allowed origin: ${FRONTEND_ORIGIN}`);
});
