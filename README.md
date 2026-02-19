# 🐝 AutoTool — Auto Rejoin Roblox (Android)

> Tool tự động khởi động lại và rejoin game Roblox trên Android, hỗ trợ nhiều clone app cùng lúc. Chạy trong Termux với quyền root.

---

## 📋 Yêu cầu

| Thứ | Chi tiết |
|-----|----------|
| Thiết bị | Android có **root** |
| App | [Termux](https://f-droid.org/packages/com.termux/) (tải từ F-Droid, không dùng bản Play Store) |
| Clone app | Các bản clone Roblox đã được cài sẵn (ví dụ: `com.zamdepzai.clienv`, `com.zamdepzai.clienw`, ...) |
| Quyền | Termux phải được cấp quyền **Storage** và **root (su)** |

---

## 🚀 Cài đặt (Setup lần đầu)

### Bước 1 — Clone repo về máy

Mở Termux, chạy lệnh sau:

```bash
cd /sdcard/Download
git clone https://github.com/Jakiduy1410/AutoTool.git
cd AutoTool
```

### Bước 2 — Cài dependencies

Chạy script bootstrap để cài Python, git và các gói cần thiết:

```bash
bash scripts/bootstrap_termux.sh
```

Script này sẽ tự động:
- Cài `python`, `git`, `rsync`, `procps`, `iproute2`, `tsu`
- Cấp quyền storage cho Termux (`termux-setup-storage`)
- Tạo thư mục làm việc tại `/sdcard/Download/AutoTool`

> ⚠️ Sau khi chạy `termux-setup-storage`, nhớ **bấm "Allow"** khi Android hỏi quyền.

---

## ⚙️ Cấu hình

### Bước 3 — Set package prefix

Mở menu chính:

```bash
bash ui/menu.sh
```

Chọn **[3] Set Package Prefix** và nhập prefix của các clone app bạn đang dùng.

Ví dụ: nếu clone app của bạn tên là `com.zamdepzai.clienv` thì prefix là `zam` hoặc `zamdepzai`.

### Bước 4 — Scan clone packages

Chọn **[4] Check User Setup** để tool tự động tìm tất cả clone app khớp với prefix vừa nhập và lưu vào `config/packages.json`.

```
✅ package_prefix = zam
Tìm thấy:
 1. com.zamdepzai.clienv
 2. com.zamdepzai.clienw
```

### Bước 5 — Chọn game

Chọn **[2] Scan Packages + Select Game ID** để chọn game muốn auto rejoin.

Danh sách game có sẵn trong `config/games.json`. Hiện tại mặc định là **Bee Swarm Simulator** (placeId `1537690962`).

Để thêm game khác, sửa file `config/games.json`:

```json
{
  "games": [
    { "name": "Bee Swarm Simulator", "placeId": 1537690962 },
    { "name": "Pet Simulator X",     "placeId": 1294081203 }
  ]
}
```

---

## ▶️ Chạy Auto Rejoin

Sau khi setup xong, mở menu:

```bash
bash ui/menu.sh
```

Chọn **[1] Join Game + Start Watchdog + Status**

Tool sẽ:
1. Khởi động **Watchdog** chạy nền
2. Tự động mở từng clone app
3. Gửi lệnh join game vào từng clone
4. Hiển thị dashboard trạng thái real-time

---

## 🔍 Cách Watchdog hoạt động

```
┌─────────────────────────────────────────┐
│            Watchdog (mỗi 5 giây)        │
│                                         │
│  Kiểm tra PID của từng clone app        │
│          │                              │
│    App đang chạy? ──── YES ──► OK       │
│          │                              │
│         NO                              │
│          │                              │
│   PID trước đó có không?                │
│    YES ──► CRASHED ──► Restart + Join   │
│    NO  ──► CHƯA CHẠY ──► Start + Join   │
│                                         │
│  Sau mỗi action: cooldown 30 giây       │
└─────────────────────────────────────────┘
```

**Các trạng thái của clone:**

| Trạng thái | Ý nghĩa |
|------------|---------|
| `RUNNING`  | App đang chạy bình thường |
| `CRASHED`  | App bị crash, đang restart |
| `NOT_RUNNING` | App chưa được khởi động |
| `COOLDOWN` | Đang chờ sau khi restart |

---

## 📁 Cấu trúc thư mục

```
AutoTool/
├── bin/
│   ├── start_watchdog.sh       # Khởi động watchdog
│   └── stop_watchdog.sh        # Dừng watchdog
├── config/
│   ├── engine.json             # Cấu hình watchdog (interval, cooldown...)
│   ├── games.json              # Danh sách game
│   ├── global.json             # Game đang chọn + join URL
│   └── packages.json           # Danh sách clone packages
├── engine/
│   └── watchdog.py             # Engine chính (Python)
├── scripts/
│   └── bootstrap_termux.sh     # Cài đặt dependencies
├── ui/
│   ├── menu.sh                 # Menu chính
│   └── status.sh               # Dashboard trạng thái
└── workflows/
    ├── check_user_setup.sh     # Scan clone packages
    ├── scan_and_check.sh       # Scan + test join thủ công
    ├── set_package_prefix.sh   # Set prefix
    ├── setup_game_and_packages.sh  # Chọn game
    └── start_auto_rejoin.sh    # Bật auto rejoin
```

---

## ⚙️ Tinh chỉnh cấu hình

Sửa file `config/engine.json` để điều chỉnh hành vi watchdog:

```json
{
  "interval_sec": 5,      // Tần suất kiểm tra (giây)
  "cooldown_sec": 30,     // Thời gian chờ sau khi restart
  "start_grace_sec": 10   // Thời gian chờ app load trước khi join
}
```

---

## 📝 Log

Log được lưu tại:
```
/sdcard/Download/AutoTool/logs/watchdog.log
```

Ví dụ log:
```
[2025-01-01 12:00:00] WATCHDOG_START interval=5s cooldown=30s grace=10s join=YES
[2025-01-01 12:00:35] [com.zamdepzai.clienv] CRASHED reason=pid_lost action=RESTART+JOIN
[2025-01-01 12:01:10] [com.zamdepzai.clienw] NOT_RUNNING reason=pid_none action=START+JOIN
```

---

## ❓ Troubleshooting

**Không tìm thấy package nào:**
→ Kiểm tra lại prefix. Chạy `pm list packages | grep <prefix>` trong Termux để xác nhận.

**Watchdog không restart được app:**
→ Đảm bảo Termux đã được cấp quyền root. Thử chạy `su -c "echo ok"` để kiểm tra.

**App mở lên nhưng không vào game:**
→ Kiểm tra `join_url` trong `config/global.json`. Đảm bảo placeId đúng và tài khoản đã đăng nhập sẵn trong clone app.

**`termux-setup-storage` không hoạt động:**
→ Vào Settings → Apps → Termux → Permissions → Files and media → Allow.

---

## 📌 Lưu ý

- Tool yêu cầu **quyền root** để gửi lệnh `am start` và `force-stop` app.
- Mỗi clone app cần phải **đã đăng nhập Roblox sẵn** trước khi bật watchdog.
- Tính năng Phase 4 (menu [5] và [6]) chưa được implement.
