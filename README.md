# 📊 Exness MT5 Breakout Alert Bot

🚀 A fully automated **breakout detection bot** that connects to your **Exness MT5 terminal**, computes **session highs & lows**, and sends you **Telegram alerts** whenever price breaks out of key levels.

---

## ✨ Features

✅ **Multi-symbol support** (auto-detects broker suffixes, e.g. `EURUSDm`, `XAUUSDm`)  
✅ **Session Levels (IST):**  
   - Previous Day → `23:30 – 05:29`  
   - Asian Session → `05:30 – 12:29`  
   - London Session → `12:30 – 17:30`  
✅ **Daily Reset @ 23:00 IST** → Recomputes all levels & clears alerts  
✅ **Breakout Confirmation on closed M5 candles** (no false tick spikes)  
✅ **Telegram Alerts** in a clean format:  


✅ **Alert Throttling Policy:**  
- 1st alert → always sent  
- 2nd alert → always sent  
- 3rd+ alerts → only if **30 minutes passed since last alert**

✅ **Daily Level Report** (PDH, PDL, AH, AL) sent automatically to Telegram  

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/MT5_Levels_Bot.git
cd MT5_Levels_Bot
