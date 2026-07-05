import os
import json
import subprocess
import traceback
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"
LOG_FILE = "error_log.txt"

class ControlPanelApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Video Generator - Master Settings Panel v2.3")
        self.geometry("680x850") 
        self.resizable(False, False)

        # টাইটেল
        self.title_label = ctk.CTkLabel(self, text="AI Video Automation Config Manager", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(pady=15)

        # ১. আরএসএস ইউআরএল (একাধিক দেওয়া যাবে কমা দিয়ে)
        ctk.CTkLabel(self, text="Target RSS Feed URLs (comma separated for multiple feeds):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.url_entry = ctk.CTkEntry(self, width=600, height=35)
        self.url_entry.pack(padx=40, pady=(0, 8))

        # ২. টাইটেল নিষিদ্ধ কিওয়ার্ড ফিল্টার
        ctk.CTkLabel(self, text="Exclude Keywords in Title (comma separated):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.keyword_entry = ctk.CTkEntry(self, width=600, height=35)
        self.keyword_entry.pack(padx=40, pady=(0, 8))

        # ৩. আর্টিকেলের ভেতরের নিষিদ্ধ কিওয়ার্ড ফিল্টার
        ctk.CTkLabel(self, text="Exclude Keywords inside Article Body (comma separated):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.body_keyword_entry = ctk.CTkEntry(self, width=600, height=35)
        self.body_keyword_entry.pack(padx=40, pady=(0, 8))

        # ৪. মিনিমাম ওয়ার্ড ফিল্টার
        ctk.CTkLabel(self, text="Minimum Article Word Count (to make video):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.word_count_entry = ctk.CTkEntry(self, width=600, height=35, placeholder_text="e.g. 200")
        self.word_count_entry.pack(padx=40, pady=(0, 8))

        # ৫. আর্টিকেল টাইমিং রেঞ্জ ফিল্টার (সম্পূর্ণ ফ্লেক্সিবল ইনপুট)
        ctk.CTkLabel(self, text="Max Article Age in Hours (e.g. 1 for 1 hour, 0.5 for 30 mins, 9999 for All Articles):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.age_entry = ctk.CTkEntry(self, width=600, height=35, placeholder_text="e.g. 24")
        self.age_entry.pack(padx=40, pady=(0, 8))

        # ৬. ভয়েস সিলেকশন
        ctk.CTkLabel(self, text="Select AI Voice:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.voices_list = [
            "en-US-BrianNeural (US Male - Deep/Professional)",
            "en-US-GuyNeural (US Male - Casual)",
            "en-GB-RyanNeural (UK Male - Elegant)"
        ]
        self.voice_combo = ctk.CTkComboBox(self, values=self.voices_list, width=600)
        self.voice_combo.pack(padx=40, pady=(0, 8))

        # ७. সাবটাইটেল টেক্সট কালার
        ctk.CTkLabel(self, text="Subtitle Text Color (HEX):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.text_color_entry = ctk.CTkEntry(self, width=600, height=35)
        self.text_color_entry.pack(padx=40, pady=(0, 8))

        # ৮. ওভারলে কালার
        ctk.CTkLabel(self, text="Background Overlay Color (HEX):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.bg_color_entry = ctk.CTkEntry(self, width=600, height=35)
        self.bg_color_entry.pack(padx=40, pady=(0, 8))

        # ৯. ওভারলে ব্যাকগ্রাউন্ড স্টাইল
        ctk.CTkLabel(self, text="Overlay Style:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=40, pady=(8, 2))
        self.style_combo = ctk.CTkComboBox(self, values=["Semi-Transparent Box (Style 3)", "Outline + Drop Shadow (Style 1)"], width=600)
        self.style_combo.pack(padx=40, pady=(0, 8))

        # ১০. ফন্ট সাইজ এবং পজিশন স্লাইডার
        self.slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.slider_frame.pack(fill="x", padx=40, pady=10)

        self.font_size_slider = ctk.CTkSlider(self.slider_frame, from_=12, to=36, number_of_steps=24, width=280)
        self.font_size_slider.pack(side="left", padx=(0, 20))
        self.font_size_slider.set(22)
        
        self.margin_v_slider = ctk.CTkSlider(self.slider_frame, from_=20, to=150, number_of_steps=26, width=280)
        self.margin_v_slider.pack(side="right")
        self.margin_v_slider.set(45)

        # সেভ এবং পুশ বাটন
        self.save_btn = ctk.CTkButton(
            self, 
            text="💾 Save & Sync Settings with GitHub Cloud", 
            fg_color="#2ecc71", 
            hover_color="#27ae60",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            command=self.save_and_push
        )
        self.save_btn.pack(pady=15, fill="x", padx=40)

        self.status_lbl = ctk.CTkLabel(self, text="Status: Idle", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_lbl.pack()

        self.load_defaults()

    def load_defaults(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.url_entry.insert(0, data.get("rss_urls", ""))
                self.keyword_entry.insert(0, data.get("exclude_title_keywords", ""))
                self.body_keyword_entry.insert(0, data.get("exclude_body_keywords", ""))
                self.word_count_entry.insert(0, str(data.get("min_word_count", 200)))
                self.age_entry.insert(0, str(data.get("max_age_hours", 24.0)))
                self.voice_combo.set(data.get("voice", ""))
                self.text_color_entry.insert(0, data.get("font_color", ""))
                self.bg_color_entry.insert(0, data.get("bg_color", ""))
                self.style_combo.set("Semi-Transparent Box (Style 3)" if data.get("border_style") == 3 else "Outline + Drop Shadow (Style 1)")
                self.font_size_slider.set(data.get("font_size", 22))
                self.margin_v_slider.set(data.get("margin_v", 45))
                return
            except Exception:
                pass

        # অলটারনে티브 ডিফল্টস 
        self.url_entry.insert(0, "https://sports.yahoo.com/nba/rss.xml, https://sports.yahoo.com/nfl/rss.xml")
        self.keyword_entry.insert(0, "odds, fantasy, betting, bet, spread, draft, preview")
        self.body_keyword_entry.insert(0, "injury, out indefinitely, legal, court, police, arrested")
        self.word_count_entry.insert(0, "200")
        self.age_entry.insert(0, "24") 
        self.text_color_entry.insert(0, "#FFFFFF")
        self.bg_color_entry.insert(0, "#000000")
        self.style_combo.set("Semi-Transparent Box (Style 3)")

    def save_and_push(self):
        self.save_btn.configure(state="disabled")
        self.status_lbl.configure(text="Saving configs & Syncing with GitHub...", text_color="yellow")
        self.update()

        border_style = 3 if "Box" in self.style_combo.get() else 1
        
        try:
            min_word_val = int(self.word_count_entry.get().strip())
        except ValueError:
            min_word_val = 200

        try:
            max_age_val = float(self.age_entry.get().strip())
        except ValueError:
            max_age_val = 24.0

        config_data = {
            "rss_urls": self.url_entry.get().strip(),
            "exclude_title_keywords": self.keyword_entry.get().strip(),
            "exclude_body_keywords": self.body_keyword_entry.get().strip(),
            "min_word_count": min_word_val,
            "max_age_hours": max_age_val,
            "voice": self.voice_combo.get().split(" ")[0],
            "font_color": self.text_color_entry.get().strip(),
            "bg_color": self.bg_color_entry.get().strip(),
            "border_style": border_style,
            "bg_opacity": 0.6,  
            "font_size": int(self.font_size_slider.get()),
            "margin_v": int(self.margin_v_slider.get())
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        try:
            subprocess.run(["git", "add", CONFIG_FILE], check=True)
            subprocess.run(["git", "commit", "-m", "Master Configurations Updated [skip ci]"], check=True)
            subprocess.run(["git", "push"], check=True)
            self.status_lbl.configure(text="SUCCESS! New rules synced with GitHub Cloud.", text_color="#2ecc71")
        except Exception as e:
            self.status_lbl.configure(text="Git Sync Failed! Check logs.", text_color="red")
            with open(LOG_FILE, "a") as lf:
                lf.write(traceback.format_exc() + "\n")
        finally:
            self.save_btn.configure(state="normal")

if __name__ == "__main__":
    app = ControlPanelApp()
    app.mainloop()
