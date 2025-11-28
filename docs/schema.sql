-- Adminer 5.4.0 PostgreSQL 17.6 dump

DROP TABLE IF EXISTS "bids";
DROP SEQUENCE IF EXISTS bids_id_seq;
CREATE SEQUENCE bids_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."bids" (
    "id" integer DEFAULT nextval('bids_id_seq') NOT NULL,
    "project_id" integer NOT NULL,
    "freelancer_id" integer NOT NULL,
    "price" integer NOT NULL,
    "message" text,
    "created_at" timestamp DEFAULT now() NOT NULL,
    CONSTRAINT "bids_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);

CREATE UNIQUE INDEX bids_project_id_freelancer_id_key ON public.bids USING btree (project_id, freelancer_id);

INSERT INTO "bids" ("id", "project_id", "freelancer_id", "price", "message", "created_at") VALUES
(13,	16,	10,	3000,	'現在是某公司的 3D 模型計畫相關的研究助理，有相關作品。',	'2025-11-07 17:18:45.622967'),
(14,	18,	10,	3500,	'曾任遊戲開發設計工程師，可幫忙協助測試有無bug。
也可以協助增加新功能，不過價格需另談(可附相關遊戲開發經驗證明)
需要可詳談~~',	'2025-11-07 17:20:24.516004'),
(15,	14,	10,	2000,	'曾住在日本東京附近實習3年，對附近還算熟悉，可以協助規劃！',	'2025-11-07 17:21:49.557732'),
(16,	15,	10,	3000,	'有其他類型的影片拍攝經驗，餐廳類的還沒，但願意學習，會附上以往作品',	'2025-11-07 17:23:51.416302'),
(17,	22,	10,	60000,	'現任某公司外聘全端工程師，符合條件，可提供相關證明及作品',	'2025-11-07 17:31:49.088129'),
(18,	20,	10,	1800,	'是 Netflix, Disney+ 的愛用者，兩個皆訂閱超過 3 年',	'2025-11-07 17:32:48.963562'),
(19,	19,	10,	1000,	'可協助',	'2025-11-07 17:48:24.168266'),
(20,	22,	13,	70000,	'可以協助測試!',	'2025-11-07 17:51:00.476399'),
(21,	20,	13,	1500,	'兩大平台愛用者 可以協助訪談~',	'2025-11-07 17:51:42.103496');

DROP TABLE IF EXISTS "deliveries";
DROP SEQUENCE IF EXISTS deliveries_id_seq;
CREATE SEQUENCE deliveries_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."deliveries" (
    "id" integer DEFAULT nextval('deliveries_id_seq') NOT NULL,
    "project_id" integer NOT NULL,
    "freelancer_id" integer NOT NULL,
    "filename" character varying(200) NOT NULL,
    "note" text,
    "created_at" timestamp DEFAULT now() NOT NULL,
    CONSTRAINT "deliveries_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);

INSERT INTO "deliveries" ("id", "project_id", "freelancer_id", "filename", "note", "created_at") VALUES
(12,	18,	10,	'version.png',	'測試測試',	'2025-11-07 17:41:49.508313'),
(13,	14,	10,	'1141 SE 期中專題.pptx',	'規劃書如檔案',	'2025-11-07 17:43:44.913722'),
(15,	19,	10,	'2CE1E7CC-E03F-44CE-BBFE-D28426749A98.jpg',	'hello',	'2025-11-07 17:50:03.914941');

DROP TABLE IF EXISTS "projects";
DROP SEQUENCE IF EXISTS projects_id_seq;
CREATE SEQUENCE projects_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."projects" (
    "id" integer DEFAULT nextval('projects_id_seq') NOT NULL,
    "title" character varying(100) NOT NULL,
    "description" text,
    "status" character varying(20) DEFAULT 'open' NOT NULL,
    "client_id" integer NOT NULL,
    "created_at" timestamp DEFAULT now() NOT NULL,
    "awarded_bid_id" integer,
    "budget" integer,
    CONSTRAINT "projects_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);

INSERT INTO "projects" ("id", "title", "description", "status", "client_id", "created_at", "awarded_bid_id", "budget") VALUES
(14,	'協助安排日本自由行旅遊規劃',	'協助事項：
• 協助我 12 月出國前，我已經先整理好行程與交通方式。
• 一起討論如何讓行程安排更順暢。
• 會有一些關於東京地點的詢問，需要提供建議或路線規劃。
工作方式：
• 線上討論即可（文字或語音）。
• 時間彈性，視雙方討論進度調整。',	'closed',	9,	'2025-11-07 16:59:45.909976',	15,	2000),
(16,	'3D模型產品設計',	'【幫忙事項】：修改設計一個吉他的琴橋造型
【條件】：曾接觸過 3D 模型設計，且有相關作品
【討論方式】：希望接案後和繳交檔案前各進行一次實體討論及修改
【酬勞】：預算是2000元，但依照實際情況(作品完成度)會再往上調整(最高至$5000元)
【討論地點】高雄市苓雅區(地點詳談)',	'reopened',	9,	'2025-11-07 17:09:09.320703',	13,	2000),
(17,	'徵剪輯影片小編',	'【處理事項】：幫忙協助我的自媒體運作(服飾店短影音)
【交付方式】：檔案
【交付期限】：先面談後再決定
【注意事項】：希望是平常是喜歡看穿搭影片者，因為需要一些穿搭相關評語
【面談地點】：台北市松山區
【酬勞支付】：限匯款 一支影片$1000(每個月最高5支)
【注意事項】：
  這是長期的工作合作，但由於工時不一定，所以算是小外快的感覺，不算是正職有固定工時，可以接受者再來， 感謝。',	'open',	12,	'2025-11-07 17:14:47.029906',	NULL,	1000),
(20,	'1小時串流平台線上訪談',	'【幫忙事項】：目前正在尋找50名符合以下條件的參與者，參加串流平台產品研究訪談：
1.目前有訂閱至少兩個以上串流平台（Netflix,Disney+等）
2.使用android手機
3.線上訪談
4.請先填寫前測篩選問卷：（約五分鐘時間）
5.前測篩選通過會以信件通知
研究主題：串流平台觀看經驗
研究單位：賣噹噹
報酬：1800 元台幣
',	'open',	9,	'2025-11-07 17:25:12.805524',	NULL,	1800),
(15,	'短影音剪輯拍攝🎬',	'【主辦單位】： 羊老饕
【幫忙事項】：拍攝短影音一支，含完成剪輯
【注意事項】：
  - 請提供過往作品
  - 可以的話盡量以線上通話的方式進行拍攝內容討論
【公司地址】：雲林縣麥寮鄉中興路
【支付酬勞】：匯款為主
',	'in_progress',	9,	'2025-11-07 17:02:36.869609',	16,	3000),
(22,	'全端工程師開發AI修圖平台',	'我們正在尋找一位能快速實作原型的 全端工程師 / AI 工程師，負責打造一個簡潔、可用的 AI 修圖平台（AI Photo Editor）。使用者能上傳圖片、輸入提示文字（prompt），進行局部修圖、上色、去除背景、或重生成畫面。
🚀 你將負責
建立前端頁面（React / Next.js / MUI）
串接 AI 模型 API（如 Replicate, Stability, OpenAI, Hugging Face）
實作圖片上傳、即時預覽、修圖區塊選擇（inpainting / background removal）
儲存與管理生成結果（Firebase / Cloud Storage）
🧠 我們希望你具備
熟悉 React / Next.js / Node.js / Firebase
有串接過 AI 圖像生成或修圖 API
注重使用者體驗（UI/UX）與效能
📦 交付物範圍（MVP）
使用者可上傳圖片
可選修圖區域 + 輸入文字提示
生成新圖與預覽
可下載結果（PNG）
基本錯誤處理與 UI 提示',	'open',	9,	'2025-11-07 17:29:51.604424',	NULL,	60000),
(18,	'遊戲操作測試',	'【處理事項】：協助測試遊戲地圖運行流暢
【時間】：11/6、11/7 14:00-22:00
【酬勞】單次$3500
【交付方式】：現金、轉帳、線上支付
【交付期限】：現結
【注意事項】：有rpg類遊戲經驗佳，但內容較重複枯燥，有耐心者加分',	'in_progress',	12,	'2025-11-07 17:16:07.559615',	14,	3500),
(19,	'商品設計排版',	'【處理事項】：
  商品排版設計，需排版設計一個產品的包裝，到時會提供希望的色系，可能有部分小圖示需要繪製
【交付方式】：匯款
【交付期限】：11/12
【注意事項】：會提供產品規格、文案，完成後需要提供pdf及ai檔
',	'closed',	12,	'2025-11-07 17:16:52.871923',	19,	800),
(21,	'離散數學解題',	'【作業範圍】：Licas,Catalan,Recurrence relations
【交付方式】：完成後匯款
【注意事項】：協助輔導解題',	'open',	9,	'2025-11-07 17:29:25.038209',	NULL,	300),
(24,	'123',	'123',	'open',	9,	'2025-11-08 16:35:37.812082',	NULL,	5000);

DROP TABLE IF EXISTS "users";
DROP SEQUENCE IF EXISTS users_id_seq;
CREATE SEQUENCE users_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."users" (
    "id" integer DEFAULT nextval('users_id_seq') NOT NULL,
    "username" character varying(50) NOT NULL,
    "password_hash" character varying(128) NOT NULL,
    "role" character varying(20) NOT NULL,
    "full_name" character varying(100),
    "phone" character varying(32),
    "agreed_privacy" boolean DEFAULT false,
    "email" text,
    CONSTRAINT "users_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "users_role_check" CHECK ((role)::text = ANY ((ARRAY['client'::character varying, 'freelancer'::character varying])::text[]))
)
WITH (oids = false);

CREATE UNIQUE INDEX users_username_key ON public.users USING btree (username);

CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);

CREATE UNIQUE INDEX users_username_uniq ON public.users USING btree (username);

INSERT INTO "users" ("id", "username", "password_hash", "role", "full_name", "phone", "agreed_privacy", "email") VALUES
(9,	'client',	'$2b$12$IsqDVoWLiC6rOBnk/ysYse2N95CyZCAvfDIy1GG9amKi2xmydo8uC',	'client',	'歐陽羊羊',	'0900000000',	'f',	'client@gmail.com'),
(13,	'ttt',	'$2b$12$LzFFiC8IDQchO4GcsdJane4DGHj9JvrEeuovJJAD9jYwZ9gd8Utcm',	'freelancer',	'ttt',	'0910202039',	'f',	'ttt@gmail.com'),
(12,	'testuser',	'$2b$12$WkvcVBvQ959w7rsl3IH2OOJq0k.uSgae6YwRnNfB7H32xIEU1gctq',	'client',	'testuser',	'0910294924',	'f',	'testuser@gmail.com'),
(10,	'freelancer',	'$2b$12$7G5XhV0/Hb0PbZYcA0MyAe1v8mutv9kGuteQBzmFgHphrQ9S7cDLW',	'freelancer',	'Kevin',	'09111111121',	'f',	'kevin@gmail.com');

ALTER TABLE ONLY "public"."bids" ADD CONSTRAINT "bids_freelancer_id_fkey" FOREIGN KEY (freelancer_id) REFERENCES users(id) NOT DEFERRABLE;
ALTER TABLE ONLY "public"."bids" ADD CONSTRAINT "bids_project_id_fkey" FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."deliveries" ADD CONSTRAINT "deliveries_freelancer_id_fkey" FOREIGN KEY (freelancer_id) REFERENCES users(id) NOT DEFERRABLE;
ALTER TABLE ONLY "public"."deliveries" ADD CONSTRAINT "deliveries_project_id_fkey" FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."projects" ADD CONSTRAINT "projects_awarded_bid_id_fkey" FOREIGN KEY (awarded_bid_id) REFERENCES bids(id) NOT DEFERRABLE;
ALTER TABLE ONLY "public"."projects" ADD CONSTRAINT "projects_client_id_fkey" FOREIGN KEY (client_id) REFERENCES users(id) NOT DEFERRABLE;

-- 2025-11-28 09:41:59 UTC
