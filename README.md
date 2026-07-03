## AI自動選字助手
專案簡介
本專案為一款繁體中文微軟注音的鍵盤外掛智慧助手。透過 Python 監聽底層鍵盤與滑鼠事件，在不改變使用者原有輸入習慣的前提下，串接雲端 Gemini API 並融合本地端 Viterbi 統計語言模型，達到動態精準自動選字與長句優化的效果。

# 核心運作原理

# 1. 候選詞生成機制
當使用者按下 Ctrl + ↓ 時，系統會即時攔截尚未確定輸入的字根buffer，並依序執行以下步驟：

本地精準快取：檢索本地端字典，若有使用者親自採納過的完全相同字根組合，則優先推薦。

本地 Viterbi 預測：利用本地端學習到的詞頻與上下文轉移權重進行斷詞，在離線或雲端超限時提供局部預測。

雲端 Gemini 預測：若在本地端找不到能合適匹配輸入的資料，便將上下文與注音字根發送至 Gemini API，利用大模型理解前後文語境，生成符合邏輯的長句候選。

# 2. 監聽並主動自學習
AI 面板學習：使用者在 AI 候選視窗中按下數字鍵採納選項後，該字根與中文字將直接綁定並固化寫入本地快取。

常規打字學習：使用者常規打字按下 Enter 時，系統會自動擷取上屏的實體中文字，同步反向計算注音字根以更新模型。

---
以下為程式執行範例:

windows内建選字容易出錯:

<img width="500" height="285" alt="image" src="https://github.com/user-attachments/assets/0f7385e9-63a1-4bdf-8ab4-e0dafa8b43a1" />

在輸入完句子後能夠直接按下ctrl+向下鍵進行選字:

<img width="500" height="282" alt="image" src="https://github.com/user-attachments/assets/acb4cbb8-47b9-4ed7-b206-8e119589ae8b" />

選完後程式取代原先的錯誤選字，並將選習到的資料存入本地端詞庫當中:

<img width="500" height="282" alt="image" src="https://github.com/user-attachments/assets/5de4b213-77fa-42bf-9ed6-ee9318bcc609" />


---
本程式預計加入本地端深度學習模型，透過將gemini推論的正確資料餵給transformer模型並讓本地端模型在不斷學習的過程中不斷減少雲端模型用量。
