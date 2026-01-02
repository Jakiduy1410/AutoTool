File auto rejoin của Jakiduy :)))

Ok, t **tóm tắt lại dự án này ở mức “nhắc lại là làm tiếp được ngay”**, đúng mục tiêu của m.
Coi như đây là **bản ghi nhớ kỹ thuật**.

---

# 🧠 TÓM TẮT DỰ ÁN AUTOTOOL (HIỆN TẠI)

## 1️⃣ MỤC TIÊU TỔNG THỂ

Đây là **CLI Automation Tool chạy trên Android (UG phone / Termux)**, dùng để:

* Quản lý **nhiều clone Roblox**
* Tự động:

  * setup UserID
  * launch game theo GameID
  * auto rejoin khi game chết
* Có UI dạng **menu + log** (không phải app đồ họa)
* Hướng tới style **executor / tool hacker** (log-driven UI)

PC / VSCode **chỉ dùng để test UI**, không phải môi trường chạy thật.

---

## 2️⃣ KIẾN TRÚC TỔNG THỂ

```
AutoTool
├─ manager.py        # Entry point + UI + điều phối
├─ config/
│   └─ config.json   # ENV + package + game_id + interval
├─ core/             # Logic thật
│   ├─ auto_rejoin.py
│   ├─ process.py
│   ├─ packages.py
│   ├─ gameid.py
│   ├─ activity_detect.py
│   ├─ user_detect.py
│   ├─ state.py      # ĐÃ CÓ – chưa dùng trong UI
│   └─ monitor.py    # ĐÃ TẠO – hiện mock / trống
├─ ui/               # UI phụ (chưa dùng)
│   ├─ menu.py
│   ├─ dashboard.py
│   ├─ log_screen.py
│   └─ layout.py
└─ setup.sh          # Chạy tool trên Android (root)
```

---

## 3️⃣ ENV & TRIẾT LÝ CHẠY

### ENV = `"pc"`

* Dùng để:

  * test UI
  * test flow phím
* **KHÔNG chạy Android command**
* Có thể mock state

### ENV = `"android"`

* Chạy thật trên UG phone
* Có:

  * `pm`, `am`, `dumpsys`, `pidof`
  * root
* Auto rejoin hoạt động thật

👉 ENV được đọc từ `config/config.json`

---

## 4️⃣ MANAGER.PY (TRẠNG THÁI HIỆN TẠI)

### Vai trò

* Là **entry point**
* Quản lý:

  * curses UI (menu + log)
  * start / stop thread
* **KHÔNG chứa logic Android**

### Hiện đã làm được

* Hiển thị menu:

  ```
  [1] Start Auto Rejoin
  [2] Scan Packages
  [3] Set GameID (Android only)
  [4] Detect UserID (Android only)
  [0] Exit
  ```
* Có cửa sổ log cuộn
* Bấm `[1]`:

  * init `state`
  * start `auto_rejoin` thread
* Bấm `[2]`:

  * scan package theo prefix
* UI ổn định trên Windows (đã xử lý curses lỗi)

📌 **UI hiện tại là UI GỐC**, được giữ nguyên có chủ đích.

---

## 5️⃣ CORE – LOGIC THẬT

### 🔹 `process.py`

* Giao tiếp Android:

  * `is_running(pkg)` → check app sống
  * `force_stop(pkg)`
  * `start_app(pkg, uri)`
* Dùng `am`, `pidof`
* **Chỉ dùng ở Android**

---

### 🔹 `packages.py`

* Scan clone:

  * `pm list packages`
  * lọc theo `package_prefix`
* Lưu danh sách clone vào `config.json`

---

### 🔹 `gameid.py`

* Map:

  ```
  package → roblox://placeID=xxxx
  ```
* Dùng để launch đúng map cho từng clone

---

### 🔹 `auto_rejoin.py`

* **Trái tim tool**
* Logic:

  * Loop vô hạn
  * Với mỗi package:

    * nếu app chết:

      * force-stop
      * start lại bằng game URI
      * chờ ổn định
  * Sleep theo interval

👉 Hiện tại:

* Đã chạy được
* Chưa gắn `state` sâu
* Chưa có detect treo loading

---

### 🔹 `activity_detect.py`

* Detect activity launch
* Chuẩn bị cho mở rộng
* Hiện **chưa dùng**

---

### 🔹 `user_detect.py`

* Detect `userId` Android bằng dumpsys
* Dùng cho setup UserID
* Chưa nối vào auto flow

---

## 6️⃣ STATE (RẤT QUAN TRỌNG)

### `state.py`

* Là **single source of truth**
* Lưu:

  ```
  {
    pkg: {
      status,
      since
    }
  }
  ```
* Trạng thái dự kiến:

  ```
  INIT
  RUNNING
  DEAD
  RESTARTING
  COOLDOWN
  ```

### Hiện tại

* ĐÃ:

  * tồn tại
  * được init trong `manager.py`
* CHƯA:

  * được dùng trong UI
  * được set đầy đủ trong auto_rejoin

👉 State **đang ở trạng thái “xương sống đặt sẵn”**

---

## 7️⃣ UI PHỤ (UI/ FOLDER)

* `ui/menu.py`, `dashboard.py`, `log_screen.py`
* Đã build thử
* **KHÔNG phải hướng UI chính**
* Được giữ lại để:

  * test
  * hoặc dùng sau

👉 UI mục tiêu hiện tại **KHÔNG dùng dashboard realtime**

---

## 8️⃣ PHONG CÁCH UI MỤC TIÊU (CHỐT)

Dựa trên ảnh mẫu m đưa:

* UI = **menu + log**
* Log là trung tâm
* State dùng để:

  * quyết định log
  * quyết định hành động
* Không redraw fancy
* Không dashboard realtime

👉 **CLI automation tool**, không phải curses app.

---

## 9️⃣ TRẠNG THÁI DỰ ÁN HIỆN TẠI

### ĐÃ LÀM ĐƯỢC

* Kiến trúc đúng
* Core chạy được
* Auto rejoin chạy
* UI gốc ổn định
* State đã được đặt đúng chỗ

### CHƯA LÀM (CHỦ ĐÍCH)

* Monitor realtime
* State-driven log
* Detect treo game
* Workflow tự động full như UI mẫu

---

## 🔚 CÂU GHI NHỚ CUỐI

> “Đây là AutoTool chạy trên Android, dùng menu để khởi động, log để theo dõi, state để điều khiển logic, auto_rejoin là lõi. UI không phải dashboard, mà là CLI automation theo style executor.”

Chỉ cần đọc lại đoạn này là **bắt nhịp lại ngay**.

---

Khi gặp lại, m chỉ cần nói:

* “Tiếp tục gắn state vào auto_rejoin”
* hoặc “Thiết kế workflow giống UI mẫu”
* hoặc “Bắt đầu auto setup UserID”

T sẽ tiếp tục **đúng từ điểm này**, không hỏi lại từ đầu.

TÓM TẮT 1 DÒNG (ĐỂ NHỚ)

State → điều khiển auto_rejoin → sinh log → UI chỉ hiển thị log.
Menu chỉ để bắt đầu, không phải trung tâm.