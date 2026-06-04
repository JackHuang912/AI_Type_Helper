# local_learning_db.py
import csv
import os
import time

# CSV 檔案路徑
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_training_data.csv")

def init_db():
    #初始化 CSV
    if not os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, mode='w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "BPMF_Input", "Correct_Chinese", "Context_State", "Source", "Timestamp", "Readable_Time"])
            print(" [資料初始化] CSV table")
        except Exception as e:
            print(f" 檔案建立失敗: {e}")

def save_training_pair(bpmf_str, chinese_text, context_state="開始", source="gemini_distill"):
    #儲存數據到 CSV 檔案中，供 Transformer 後續微調
    if not bpmf_str or not chinese_text: return
    try:
        # 1. 計算目前的行數作為簡易 ID
        row_count = 1
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
                row_count = sum(1 for _ in f)
        
        # 2. 取得目前時間
        now = time.time()
        readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
        
        # 3. 寫入新數據
        with open(CSV_PATH, mode='a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([row_count, bpmf_str, chinese_text, context_state, source, now, readable_time])
            
        print(f"成功寫入: ({source}): {bpmf_str} -> {chinese_text}")
    except Exception as e:
        print(f"寫入失敗: {e}")

# 初始化
init_db()