import time

# Single source of truth
STATE = {}

def init(pkg_list):
    """
    Khởi tạo state ban đầu cho các package
    """
    for pkg in pkg_list:
        STATE[pkg] = {
            "status": "DEAD",
            "since": None
        }

def set_state(pkg, status):
    """
    Update trạng thái clone
    """
    if pkg not in STATE:
        STATE[pkg] = {}

    STATE[pkg]["status"] = status
    STATE[pkg]["since"] = time.time()

def get_state():
    """
    UI đọc state tại đây
    """
    return STATE
