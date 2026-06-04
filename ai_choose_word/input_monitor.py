import keyboard
import mouse
import time
import tkinter as tk
import threading
import re

BPMF_MAP = {
    '1': 'ㄅ', '2': 'ㄉ', '3': 'ˇ', '4': 'ˋ', '5': 'ㄓ', '6': 'ˊ', '7': '˙', '8': 'ㄚ', '9': 'ㄞ', '0': 'ㄢ', '-': 'ㄦ',
    'q': 'ㄆ', 'w': 'ㄊ', 'e': 'ㄍ', 'r': 'ㄐ', 't': 'ㄔ', 'y': 'ㄗ', 'u': 'ㄧ', 'i': 'ㄛ', 'o': 'ㄟ', 'p': 'ㄣ',
    'a': 'ㄇ', 's': 'ㄋ', 'd': 'ㄎ', 'f': 'ㄑ', 'g': 'ㄕ', 'h': 'ㄘ', 'j': 'ㄨ', 'k': 'ㄜ', 'l': 'ㄠ', ';': 'ㄤ',
    'z': 'ㄈ', 'x': 'ㄌ', 'c': 'ㄏ', 'v': 'ㄒ', 'b': 'ㄖ', 'n': 'ㄙ', 'm': 'ㄩ',
    ',': 'ㄝ', '.': 'ㄡ', '/': 'ㄥ'
}

PUNCTUATION_LOOKUP = {
    ',': '，', '.': '。', '/': '？', ';': '；', '`': '～', 
    '[': '「', ']': '」', '\\': '、'
}

if 'WORD_PRE_LOOKUP' not in globals():
    WORD_PRE_LOOKUP = {}

def clean_tones_global(bpmf_str):
    if not bpmf_str: return ""
    return re.sub(re.compile(r'[ˊˇˋ˙12345 ]'), '', bpmf_str)

class SystemInputMonitor:
    def __init__(self, multi_predict_callback, learn_callback, init_callback, context_query_callback):
        self.multi_predict_callback = multi_predict_callback 
        self.learn_callback = learn_callback                 
        self.init_callback = init_callback
        self.context_query_callback = context_query_callback
        
        self.current_buffer = []
        self.has_active_menu = False
        self.candidates = []          
        self.last_bpmf_raw = ""
        
        self.is_hooked = False
        self.root = None
        self.label = None
        self.init_ui_thread()

    def init_ui_thread(self):
        def run_ui():
            self.root = tk.Tk()
            self.root.title("AI Candidate Window")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.98)
            self.root.configure(bg='#1E1E2E') 
            self.root.wm_attributes("-disabled", True)

            self.label = tk.Label(
                self.root, 
                text=" 💡 AI 智慧候選面板已就緒 ", 
                font=("Microsoft JhengHei", 12, "bold"), 
                fg="#CDD6F4", 
                bg="#1E1E2E",
                padx=16,
                pady=10,
                justify="left"
            )
            self.label.pack()
            self.root.geometry("+30+30")
            self.root.mainloop()

        ui_thread = threading.Thread(target=run_ui, daemon=True)
        ui_thread.start()

    def update_ui_text(self, text, style="normal"):
        if not self.label or not self.root: return
        try:
            if style == "active":
                self.root.configure(bg='#1E1E2E')
                self.label.configure(bg='#1E1E2E', fg='#F5C2E7', text=f"  當前字根: {text} ")
            elif style == "menu":
                self.root.configure(bg='#313244')
                self.label.configure(bg='#313244', fg='#A6E3A1', text=text)
            elif style == "success":
                self.root.configure(bg='#11111B')
                self.label.configure(bg='#11111B', fg='#89B4FA', text=f"  替換成功 ")
            else:
                self.root.configure(bg='#1E1E2E')
                self.label.configure(bg='#1E1E2E', fg='#CDD6F4', text="  AI 選字候選面板 (按下 Ctrl+↓) ")
            self.root.update()
        except Exception:
            pass

    def translate_to_bpmf(self):
        res = []
        for k in self.current_buffer:
            if k in BPMF_MAP: res.append(BPMF_MAP[k])
            elif k in PUNCTUATION_LOOKUP: res.append(PUNCTUATION_LOOKUP[k])
            else: res.append(k)
        return "".join(res)

    def trigger_ai_predictions(self):
        if not self.current_buffer: return
        
        bpmf_result = self.translate_to_bpmf()
        self.last_bpmf_raw = bpmf_result
        
        print(f" [Ctrl+↓] 正在為字根 '{bpmf_result}' 生成局部候選解...")
        self.candidates = self.multi_predict_callback(bpmf_result)
        
        if not self.candidates:
            print("無合適的候選句子!")
            return
            
        self.has_active_menu = True
        
        menu_text = f"AI 局部候選 :\n"
        for idx, cand in enumerate(self.candidates):
            menu_text += f"  [{idx + 1}] {cand}\n"
        menu_text += "  [Esc] 取消面板"
        
        self.update_ui_text(menu_text, "menu")

    def select_candidate(self, index):
        if not self.has_active_menu or index >= len(self.candidates): return
        chosen_text = self.candidates[index]
        print(f"[選取成功] 將目標項目存入本地端模型: {chosen_text}")
        
        cleaned_b = clean_tones_global(self.last_bpmf_raw)
        if cleaned_b:
            WORD_PRE_LOOKUP[cleaned_b] = chosen_text
        
        self.learn_callback(chosen_text, self.last_bpmf_raw)
        
        self.stop()
        time.sleep(0.01)
        keyboard.release('ctrl'); keyboard.release('shift'); keyboard.release('alt')
        time.sleep(0.01)
        
        bpmf_visual_string = self.translate_to_bpmf()
        backspaces_needed = len(bpmf_visual_string)
        
        print(f"[精準擦除] 當前虛線字根為 '{bpmf_visual_string}'，精準退格計數: {backspaces_needed} 次")
        
        for _ in range(backspaces_needed):
            keyboard.send('backspace')
            time.sleep(0.005) 
            
        time.sleep(0.02)
        keyboard.write(chosen_text) 
        time.sleep(0.02)
        
        keyboard.send('enter')
        time.sleep(0.02)
        
        self.update_ui_text("", "success")
        self.has_active_menu = False
        self.candidates = []
        self.current_buffer = []
        
        def safe_rehook():
            time.sleep(0.05)
            self.start()
        threading.Thread(target=safe_rehook, daemon=True).start()

    def close_menu(self):
        self.has_active_menu = False
        self.candidates = []
        self.update_ui_text("", "normal")

    def on_mouse_event(self, event):
        if isinstance(event, mouse.ButtonEvent) and event.event_type == 'down':
            if self.has_active_menu: self.close_menu()
            self.current_buffer = []

    def on_key_event(self, event):
        if event.event_type == keyboard.KEY_DOWN:
            name = event.name.lower()
            
            if self.has_active_menu:
                if name in ['1', '2', '3']:
                    val = int(name) - 1
                    self.select_candidate(val)
                    return False 
                if name == 'esc':
                    self.close_menu()
                    return True 

            if name == 'backspace':
                if self.current_buffer: 
                    self.current_buffer.pop()
                    bpmf_now = self.translate_to_bpmf()
                    if bpmf_now: self.update_ui_text(bpmf_now, "active")
                    else: self.update_ui_text("", "normal")
                return True

            if name == 'down':
                if keyboard.is_pressed('ctrl') and self.current_buffer and not self.has_active_menu:
                    self.trigger_ai_predictions()
                    return False 
                else:
                    return True

            clean_name = name.split('+')[-1]
            if clean_name in BPMF_MAP or clean_name in PUNCTUATION_LOOKUP:
                if self.has_active_menu: self.close_menu() 
                self.current_buffer.append(clean_name)
                bpmf_now = self.translate_to_bpmf()
                self.update_ui_text(bpmf_now, "active")
                return True  

            if name == 'enter':
                if self.init_callback:
                    if self.current_buffer and not self.has_active_menu:
                        raw_bpmf = self.translate_to_bpmf()
                        cleaned_b = clean_tones_global(raw_bpmf)
                        
                        # 字根清洗後必須完全相等
                        if cleaned_b in WORD_PRE_LOOKUP:
                            self.init_callback(WORD_PRE_LOOKUP[cleaned_b])
                        else:
                            self.init_callback(raw_bpmf)
                    else:
                        self.init_callback("")
                
                self.current_buffer = []
                if self.has_active_menu: self.close_menu()
                self.update_ui_text("", "normal")
                return True

            if name == 'space':
                return True

    def start(self):
        if not self.is_hooked:
            try:
                keyboard.hook(self.on_key_event, suppress=False)
                mouse.hook(self.on_mouse_event)
                self.is_hooked = True
                print("打字助手監聽就緒。")
            except Exception as e: 
                print(f"啟動失敗: {e}")

    def stop(self):
        if self.is_hooked:
            try:
                keyboard.unhook_all()
                mouse.unhook_all()
                self.is_hooked = False
                print("打字助手監聽已安全關閉。")
            except Exception: pass