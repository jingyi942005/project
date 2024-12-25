import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import Calendar
import sqlite3

# 建立資料庫連線與資料表
def init_db():
    conn = sqlite3.connect("mood_calendar.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS mood_records (
                        date TEXT PRIMARY KEY,
                        mood TEXT,
                        note TEXT)''')
    conn.commit()
    conn.close()

# 儲存情緒資料
def save_mood(date, mood, note):
    conn = sqlite3.connect("mood_calendar.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO mood_records (date, mood, note) VALUES (?, ?, ?)", (date, mood, note))
        conn.commit()
        messagebox.showinfo("成功", "情緒紀錄已儲存！")
    except Exception as e:
        messagebox.showerror("錯誤", f"無法儲存情緒紀錄: {e}")
    finally:
        conn.close()

# 查詢情緒資料
def get_mood(date):
    conn = sqlite3.connect("mood_calendar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT mood, note FROM mood_records WHERE date = ?", (date,))
    result = cursor.fetchone()
    conn.close()
    return result

# 更新選定日期的情緒紀錄
def update_mood(event):
    selected_date = calendar.get_date()
    mood_data = get_mood(selected_date)
    if mood_data:
        mood_combobox.set(mood_data[0])
        note_entry.delete("1.0", tk.END)
        note_entry.insert(tk.END, mood_data[1])
    else:
        mood_combobox.set("")
        note_entry.delete("1.0", tk.END)

# 介面設計
init_db()
root = tk.Tk()
root.title("每日情緒日曆")

# 日曆元件
calendar = Calendar(root, selectmode="day", date_pattern="yyyy-mm-dd")
calendar.grid(row=0, column=0, padx=10, pady=10, columnspan=2)
calendar.bind("<<CalendarSelected>>", update_mood)

# 情緒下拉選單
mood_label = tk.Label(root, text="選擇情緒:")
mood_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)

mood_combobox = ttk.Combobox(root, values=["😀 開心", "😐 普通", "😔 難過", "😡 生氣", "😴 疲倦"])
mood_combobox.grid(row=1, column=1, padx=5, pady=5)

# 備註文字框
note_label = tk.Label(root, text="備註:")
note_label.grid(row=2, column=0, sticky="ne", padx=5, pady=5)

note_entry = tk.Text(root, height=5, width=30)
note_entry.grid(row=2, column=1, padx=5, pady=5)

# 儲存按鈕
def save_action():
    date = calendar.get_date()
    mood = mood_combobox.get()
    note = note_entry.get("1.0", tk.END).strip()
    if not mood:
        messagebox.showwarning("警告", "請選擇情緒！")
        return
    save_mood(date, mood, note)

save_button = tk.Button(root, text="儲存", command=save_action)
save_button.grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()
