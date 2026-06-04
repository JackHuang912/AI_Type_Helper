import os
import time
import sys
import re
from pypinyin import pinyin, Style
from gemini_service import get_gemini_fallback
from input_monitor import SystemInputMonitor
from local_learning_db import save_training_pair
#處理utf-8格式
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.insert(0, current_dir)

try:
    STYLE_BPMF = Style.BPMF
except AttributeError:
    STYLE_BPMF = getattr(Style, 'BOPOMOFO', Style.NORMAL)

BPMF_TO_WORDS = {}
TRANSITION_WEIGHTS = {"開始": {"我": 10.0}}
EXACT_MATCH_CACHE = {}  # 精準完全匹配快取

global_context = "開始"
last_context = "開始"
monitor = None
IS_GEMINI_EXHAUSTED = False

def clean_bpmf_tones(bpmf_str):
    if not bpmf_str: return ""
    return re.sub(re.compile(r'[ˊˇˋ˙12345 ]'), '', bpmf_str)

def bind_word_to_bpmf_str(bpmf_str, word, context="開始", is_from_gemini=False, weight_bonus=350.0):
    if not word or not bpmf_str: return
    target_bpmf = clean_bpmf_tones(bpmf_str)
    
    if target_bpmf not in BPMF_TO_WORDS: BPMF_TO_WORDS[target_bpmf] = []
    if word not in BPMF_TO_WORDS[target_bpmf]: BPMF_TO_WORDS[target_bpmf].append(word)
    
    if context not in TRANSITION_WEIGHTS: TRANSITION_WEIGHTS[context] = {}
    bonus = 500.0 if is_from_gemini else weight_bonus
    TRANSITION_WEIGHTS[context][word] = TRANSITION_WEIGHTS[context].get(word, 1.0) + bonus

def learn_new_word_locally(sentence, context="開始", is_from_gemini=False):
    if not sentence: return
    n = len(sentence)
    
    for i in range(n):
        for j in range(i + 1, n + 1):
            sub_word = sentence[i:j]
            if not sub_word or ord(sub_word[0]) < 0x4e00 or ord(sub_word[0]) in range(0x3100, 0x312F): continue 
            
            bpmf_list = pinyin(sub_word, style=STYLE_BPMF)
            raw_b_str = "".join([item[0] for item in bpmf_list])
            sub_bpmf = clean_bpmf_tones(raw_b_str)
            
            sub_context = context if i == 0 else sentence[i-1]
            is_full_sentence = (i == 0 and j == n)
            bonus = 600.0 if is_full_sentence else 300.0
            
            bind_word_to_bpmf_str(sub_bpmf, sub_word, sub_context, is_from_gemini, weight_bonus=bonus)

def viterbi_split_and_predict(bpmf_str, context="開始"):
    if not bpmf_str: return "", 0.0
    bpmf_str = clean_bpmf_tones(bpmf_str)
    n = len(bpmf_str)
    dp = {0: [0.0, "", context]}
    
    for i in range(1, n + 1):
        best_score = -float('inf')
        best_state = [0.0, "", ""]
        for j in range(0, i):
            sub_str = bpmf_str[j:i]
            if sub_str in BPMF_TO_WORDS:
                if j in dp:
                    prev_score, prev_sentence, prev_word = dp[j]
                    for candidate in BPMF_TO_WORDS[sub_str]:
                        context_dict = TRANSITION_WEIGHTS.get(prev_word, {})
                        trans_score = context_dict.get(candidate, 1.0)
                        length_bonus = len(candidate) * 60.0
                        
                        current_score = prev_score + trans_score + length_bonus
                        if current_score > best_score:
                            best_score = current_score
                            best_state = [current_score, prev_sentence + candidate, candidate]
        if best_score > -float('inf'): dp[i] = best_state
        
    if n in dp: return dp[n][1], dp[n][0]
    return "", 0.0

def brain_get_multi_candidates(bpmf_result):
    global global_context, IS_GEMINI_EXHAUSTED, EXACT_MATCH_CACHE
    cleaned_bpmf = clean_bpmf_tones(bpmf_result)
    candidates_pool = []
    
    # 完全相同數據匹配
    if cleaned_bpmf in EXACT_MATCH_CACHE:
        print(f"字根 '{cleaned_bpmf}' 完全符合歷史紀錄")
        for w in EXACT_MATCH_CACHE[cleaned_bpmf]:
            if w not in candidates_pool: candidates_pool.append(w)

    # Viterbi 智慧組裝預測
    local_sentence, confidence = viterbi_split_and_predict(cleaned_bpmf, global_context)
    if local_sentence and local_sentence not in candidates_pool:
        candidates_pool.append(local_sentence)
        
    if len(candidates_pool) >= 2 or IS_GEMINI_EXHAUSTED:
        return candidates_pool[:3]

    # gemini 雲端支援
    try:
        gemini_sentence = get_gemini_fallback(bpmf_result, global_context)
        if gemini_sentence in ["503_ERROR", "429_ERROR", "403_ERROR", "Quota Exceeded", None]:
            IS_GEMINI_EXHAUSTED = True
        else:
            if gemini_sentence and gemini_sentence not in candidates_pool:
                candidates_pool.append(gemini_sentence)
    except Exception:
        IS_GEMINI_EXHAUSTED = True
    return candidates_pool[:3]

def brain_process_selected_learning(chosen_text, bpmf_raw):
    global global_context, last_context, EXACT_MATCH_CACHE
    last_context = global_context
    cleaned_b = clean_bpmf_tones(bpmf_raw)
    
    if not chosen_text or ord(chosen_text[0]) in range(0x3100, 0x312F): return
    
    print(f"AI 選字學習 固化精準匹配快取 ➔ '{chosen_text}' (字根: {cleaned_b})")
    learn_new_word_locally(chosen_text, last_context, is_from_gemini=True)
    
    if cleaned_b:
        if cleaned_b not in EXACT_MATCH_CACHE: EXACT_MATCH_CACHE[cleaned_b] = []
        if chosen_text not in EXACT_MATCH_CACHE[cleaned_b]: EXACT_MATCH_CACHE[cleaned_b].insert(0, chosen_text)
        
    global_context = chosen_text[-1]

def brain_learn_from_normal_enter(normal_text):
    global global_context, last_context, EXACT_MATCH_CACHE
    if not normal_text or len(normal_text.strip()) == 0: return
    
    is_pure_bpmf = all(ord(c) in range(0x3100, 0x312F) or c in "ˊˇˋ˙ " for c in normal_text)
    
    if is_pure_bpmf:
        cleaned_b = clean_bpmf_tones(normal_text)
        print(f"常規打字主動學習 偵測到落地注音字根 ➔ '{cleaned_b}'")
        return
        
    clean_text = re.sub(r'[a-zA-Z0-9\s\-_+=!@#$%^&*(),.?":{}|<>]', '', normal_text)
    if not clean_text: return
    
    last_context = global_context
    print(f"常規打字主動學習 偵測到落地文字 ➔ '{clean_text}'，加入本地資料庫失敗")
    
    learn_new_word_locally(clean_text, last_context, is_from_gemini=False)
    
    try:
        bpmf_list = pinyin(clean_text, style=STYLE_BPMF)
        calculated_b = clean_bpmf_tones("".join([item[0] for item in bpmf_list]))
        if calculated_b:
            if calculated_b not in EXACT_MATCH_CACHE: EXACT_MATCH_CACHE[calculated_b] = []
            if clean_text not in EXACT_MATCH_CACHE[calculated_b]: EXACT_MATCH_CACHE[calculated_b].append(clean_text)
            save_training_pair(calculated_b, clean_text, last_context, source="user_normal_typing")
    except Exception:
        pass
    
    global_context = clean_text[-1]

def get_current_context_state():
    return global_context

if __name__ == "__main__":
    print(" AI選字助手已啟用...")
    monitor = SystemInputMonitor(
        multi_predict_callback=brain_get_multi_candidates, 
        learn_callback=brain_process_selected_learning,     
        init_callback=brain_learn_from_normal_enter, 
        context_query_callback=get_current_context_state
    )
    monitor.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()