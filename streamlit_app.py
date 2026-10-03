import os
import time
from calendar import Calendar
from datetime import UTC, date, datetime
from html import escape

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
PRIORITY_LABELS = {"low": "Rendah", "medium": "Sedang", "high": "Tinggi"}

st.set_page_config(page_title="TaskFlow", page_icon="✓", layout="wide")
st.markdown(
    """
    <style>
    .stApp { color: #172033; }
    [data-testid="stHeader"] { background: rgba(248, 250, 252, .92); }
    [data-testid="stSidebar"] {
        background: #ffffff; border-right: 1px solid #e5e7eb; min-width: 290px;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .75rem; }
    [data-testid="stMainBlockContainer"] { max-width: 1060px; padding: 2.25rem 2rem 4rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border-color: #e5e7eb; border-radius: 14px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    }
    div.stButton > button, div.stFormSubmitButton > button {
        border-radius: 9px; min-height: 2.6rem; font-weight: 600;
    }
    button[kind="primary"] {
        background: #2563eb !important; border-color: #2563eb !important; color: #ffffff !important;
    }
    button[kind="primary"] *, [data-testid*="stBaseButton-primary"] * {
        color: #ffffff !important;
    }
    [data-testid*="stBaseButton-primary"] {
        background: #2563eb !important; border-color: #2563eb !important;
        color: #ffffff !important;
    }
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stFormSubmitButton"] button:hover {
        background: #2563eb !important; border-color: #2563eb !important;
    }
    [data-testid="stFormSubmitButton"] button p,
    [data-testid="stFormSubmitButton"] button span {
        color: #ffffff !important;
    }
    button[kind="primary"]:hover {
        background: #1d4ed8 !important; border-color: #1d4ed8 !important;
    }
    div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 18px;
    }
    div[data-testid="stMetric"] label { color: #667085 !important; }
    div[data-testid="stMetricValue"] { color: #172033 !important; font-size: 1.65rem; }
    .app-kicker { color: #2563eb; font-weight: 800; letter-spacing: .1em; font-size: .76rem; }
    .app-subtitle { color: #667085; margin-top: -.65rem; margin-bottom: 1.25rem; }
    h1, h2, h3, h4 { color: #172033 !important; letter-spacing: -.025em; }
    p, label, [data-testid="stCaptionContainer"] { color: #475467; }
    [data-testid="stSidebar"] h3 { font-size: 1rem; margin-top: .25rem; }
    [data-testid="stSidebar"] input { background: #f9fafb; }
    hr { border-color: #eaecf0; }
    .hero {
        position: relative; overflow: hidden; padding: 28px 32px; border-radius: 20px;
        color: #172033; background: linear-gradient(125deg, #eff6ff 0%, #ffffff 55%, #ecfeff 100%);
        border: 1px solid #bfdbfe; box-shadow: 0 14px 36px rgba(37, 99, 235, .10);
        margin-bottom: 1.25rem;
    }
    .hero::after {
        content: ""; position: absolute; width: 230px; height: 230px; border-radius: 50%;
        right: -70px; top: -105px; background: rgba(14,165,233,.10);
    }
    .hero-kicker {
        color: #2563eb !important; font-size: .75rem; font-weight: 800; letter-spacing: .12em;
    }
    .hero h1 { color: #172033 !important; font-size: 2rem; margin: .2rem 0 .35rem; }
    .hero h1 *, .hero p, .hero div { color: inherit; }
    .hero-copy { color: #475467 !important; margin: 0 0 1.1rem; }
    .progress-track {
        width: 100%; max-width: 520px; height: 8px;
        background: #dbeafe; border-radius: 99px;
    }
    .progress-fill { height: 8px; background: #2563eb; border-radius: 99px; }
    .progress-label { color: #344054 !important; font-size: .78rem; margin-top: .45rem; }
    .stat-card {
        background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
        padding: 16px 18px; min-height: 108px; box-shadow: 0 1px 3px rgba(16,24,40,.04);
    }
    .stat-card .stat-label { color: #667085 !important; font-size: .78rem; font-weight: 650; }
    .stat-card .stat-value {
        color: #172033 !important; font-size: 1.75rem; font-weight: 750; margin-top: .4rem;
    }
    .stat-card .stat-note { color: #98a2b3 !important; font-size: .72rem; }
    .task-title { color: #172033; font-size: 1.08rem; font-weight: 720; margin: 0 0 .35rem; }
    .task-title.done { color: #98a2b3; text-decoration: line-through; }
    .badge {
        display: inline-block; padding: 4px 9px; border-radius: 999px; margin-right: 6px;
        font-size: .72rem; font-weight: 700;
    }
    .badge-high { background: #fee4e2; color: #b42318; }
    .badge-medium { background: #fef0c7; color: #b54708; }
    .badge-low { background: #d1fadf; color: #027a48; }
    .badge-neutral { background: #f2f4f7; color: #475467; }
    .badge-overdue { background: #fff1f3; color: #c01048; }
    .empty-state { text-align: center; padding: 44px 20px; color: #667085; }
    .empty-icon { font-size: 2rem; margin-bottom: .5rem; }
    .calendar-shell {
        background: #fff; border: 1px solid #e5e7eb; border-radius: 18px;
        padding: 20px; box-shadow: 0 4px 16px rgba(16,24,40,.05);
    }
    .calendar-month { color: #172033; font-size: 1.25rem; font-weight: 750; text-align: center; }
    .calendar-weekday {
        color: #98a2b3; font-size: .7rem; font-weight: 750; text-align: center;
        text-transform: uppercase; letter-spacing: .06em; padding: .4rem 0;
    }
    .selected-date {
        padding: 14px 18px; border-radius: 12px; background: #eff6ff;
        color: #1d4ed8; font-weight: 700; margin: 1rem 0;
    }
    .calendar-legend { color: #667085; font-size: .78rem; margin: .25rem 0 1rem; }
    .legend-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin: 0 5px 0 12px; vertical-align: 1px;
    }
    .dot-selected { background: #2563eb; }
    .dot-task { background: #f59e0b; }
    .dot-today { background: #10b981; }
    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding: 1.25rem .85rem 3rem; }
        .hero { padding: 22px 20px; border-radius: 16px; }
        .hero h1 { font-size: 1.55rem; }
        .stat-card { min-height: 96px; padding: 12px; }
        .stat-card .stat-value { font-size: 1.4rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method: str, path: str, *, show_error: bool = True, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Accept"] = "application/json"
    headers["Connection"] = "close"
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(2):
        try:
            response = requests.request(
                method, f"{API_URL}{path}", headers=headers, timeout=15, **kwargs
            )
            if response.status_code == 204:
                return True
            data = response.json()
            if not response.ok:
                if show_error:
                    detail = data.get("detail", "Request gagal")
                    message = (
                        detail if isinstance(detail, str) else "Data yang dimasukkan belum valid."
                    )
                    st.error(message)
                return None
            return data
        except requests.RequestException as error:
            print(
                f"API request failed: {method} {path}: {type(error).__name__}: {error}",
                flush=True,
            )
            if attempt == 0:
                time.sleep(0.25)
                continue
        except ValueError:
            if show_error:
                st.error("API mengembalikan respons yang tidak valid.")
            return None
    if show_error:
        st.error("Koneksi ke API terputus. Coba muat ulang halaman.")
    return None


def set_flash(message: str) -> None:
    st.session_state.flash_message = message


def show_flash() -> None:
    message = st.session_state.pop("flash_message", None)
    if message:
        st.toast(message)


def reset_page() -> None:
    st.session_state.task_page = 1


def format_due_date(value: str | None, completed: bool) -> tuple[str, str]:
    if not value:
        return "Tanpa tenggat", "normal"
    due = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    overdue = due < datetime.now(UTC) and not completed
    label = due.strftime("%d %b %Y")
    return (f"Terlambat · {label}", "error") if overdue else (f"Tenggat · {label}", "normal")


def authentication_view() -> None:
    left, center, right = st.columns([1, 1.35, 1])
    with center:
        st.markdown('<p class="app-kicker">TASKFLOW</p>', unsafe_allow_html=True)
        st.title("Kelola pekerjaan dengan tenang.")
        st.markdown(
            '<p class="app-subtitle">Satu tempat sederhana untuk mencatat '
            'dan menyelesaikan task.</p>',
            unsafe_allow_html=True,
        )
        auth_mode = st.radio(
            "Pilih autentikasi",
            ["Masuk", "Buat akun"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if auth_mode == "Masuk":
            with st.form("login"):
                email = st.text_input("Email", placeholder="nama@contoh.com")
                password = st.text_input(
                    "Password akun", type="password", key="login_current_password"
                )
                submitted = st.form_submit_button("Masuk", type="primary", use_container_width=True)
                if submitted:
                    with st.spinner("Memeriksa akun..."):
                        result = api_request(
                            "POST", "/auth/login", json={"email": email, "password": password}
                        )
                    if result:
                        st.session_state.token = result["access_token"]
                        st.session_state.profile = result["user"]
                        st.rerun()
        else:
            with st.form("register"):
                email = st.text_input("Email", key="register_email", placeholder="nama@contoh.com")
                password = st.text_input(
                    "Buat password baru", type="password", key="register_new_password",
                    help="Gunakan minimal 15 karakter atau passphrase yang panjang.",
                )
                password_confirmation = st.text_input(
                    "Ulangi password baru", type="password", key="register_confirm_password"
                )
                submitted = st.form_submit_button(
                    "Buat akun", type="primary", use_container_width=True
                )
                if submitted:
                    if password != password_confirmation:
                        st.error("Konfirmasi password tidak sama.")
                    else:
                        result = api_request(
                            "POST", "/auth/register", json={"email": email, "password": password}
                        )
                        if result:
                            st.success("Akun berhasil dibuat. Silakan masuk.")


if "token" not in st.session_state:
    authentication_view()
    st.stop()

profile = st.session_state.get("profile")
if not profile:
    profile = api_request("GET", "/auth/me", show_error=False)
    if profile:
        st.session_state.profile = profile
if not profile:
    st.session_state.clear()
    st.rerun()

if "task_page" not in st.session_state:
    st.session_state.task_page = 1

with st.sidebar:
    st.markdown('<p class="app-kicker">TASKFLOW</p>', unsafe_allow_html=True)
    st.caption(profile["email"])
    st.divider()
    st.subheader("Filter")
    search = st.text_input(
        "Cari", placeholder="Cari judul atau deskripsi", on_change=reset_page
    )
    status_filter = st.selectbox(
        "Status", ["Semua", "Belum selesai", "Selesai"], on_change=reset_page
    )
    priority_filter = st.selectbox(
        "Priority", ["Semua", "Tinggi", "Sedang", "Rendah"], on_change=reset_page
    )
    overdue = st.checkbox("Hanya yang terlambat", on_change=reset_page)
    st.divider()
    st.subheader("Urutan")
    sort_label = st.selectbox("Urutkan berdasarkan", ["Terbaru", "Due date", "Priority"])
    sort_direction = st.selectbox("Arah", ["Menurun", "Menaik"])
    st.divider()
    if st.button("Keluar", use_container_width=True):
        st.session_state.clear()
        st.rerun()

summary = api_request("GET", "/tasks/summary")
if summary is None:
    st.stop()

display_name = escape(profile["email"].split("@")[0].replace(".", " ").title())
progress = round((summary["completed"] / summary["total"] * 100) if summary["total"] else 0)
st.markdown(
    f"""
    <section class="hero">
      <div class="hero-kicker">WORKSPACE PRIBADI</div>
      <h1>Selamat datang, {display_name}.</h1>
      <p class="hero-copy">Atur prioritas, tuntaskan pekerjaan, dan jaga momentum hari ini.</p>
      <div class="progress-track"><div class="progress-fill" style="width:{progress}%"></div></div>
      <div class="progress-label">
        {progress}% selesai · {summary['completed']} dari {summary['total']} task
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

action_title_col, action_col = st.columns([4, 1])
action_title_col.markdown("### Ringkasan")
show_add_form = action_col.button("+ Task baru", type="primary", use_container_width=True)
show_flash()

if show_add_form or st.session_state.get("show_add_form"):
    st.session_state.show_add_form = True
    with st.container(border=True):
        st.subheader("Buat task baru")
        with st.form("new_task", clear_on_submit=True):
            title = st.text_input("Judul", placeholder="Contoh: Selesaikan laporan mingguan")
            description = st.text_area(
                "Deskripsi", placeholder="Tambahkan detail jika diperlukan", height=90
            )
            priority_col, due_col = st.columns(2)
            priority = priority_col.selectbox("Priority", ["low", "medium", "high"], index=1)
            use_due_date = due_col.checkbox("Gunakan due date")
            due_date = due_col.date_input(
                "Tanggal", value=date.today(), disabled=not use_due_date
            )
            submit_col, cancel_col = st.columns([3, 1])
            submitted = submit_col.form_submit_button(
                "Simpan task", type="primary", use_container_width=True
            )
            cancelled = cancel_col.form_submit_button("Batal", use_container_width=True)
            if submitted:
                payload = {
                    "title": title,
                    "description": description or None,
                    "priority": priority,
                    "due_date": due_date.isoformat() if use_due_date else None,
                }
                if api_request("POST", "/tasks", json=payload):
                    st.session_state.show_add_form = False
                    set_flash("Task baru berhasil ditambahkan.")
                    st.rerun()
            if cancelled:
                st.session_state.show_add_form = False
                st.rerun()

stats = [
    ("Total task", summary["total"], "Semua pekerjaan"),
    ("Belum selesai", summary["pending"], "Perlu perhatian"),
    ("Terlambat", summary["overdue"], "Lewat tenggat"),
    ("Prioritas tinggi", summary["high_priority"], "Kerjakan lebih dulu"),
]
stat_columns = st.columns(4)
for column, (label, value, note) in zip(stat_columns, stats, strict=True):
    column.markdown(
        f'<div class="stat-card"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div><div class="stat-note">{note}</div></div>',
        unsafe_allow_html=True,
    )
st.write("")

view_mode = st.radio(
    "Tampilan", ["Daftar", "Kalender"], horizontal=True, label_visibility="collapsed"
)

if view_mode == "Kalender":
    today = date.today()
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = today.year
        st.session_state.calendar_month = today.month
        st.session_state.selected_date = today

    year = st.session_state.calendar_year
    month = st.session_state.calendar_month
    month_names = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    previous_col, month_col, today_col, next_col = st.columns([1, 4, 1.2, 1])
    if previous_col.button("←", key="previous-month", use_container_width=True):
        st.session_state.calendar_month = 12 if month == 1 else month - 1
        st.session_state.calendar_year = year - 1 if month == 1 else year
        st.session_state.selected_date = date(
            st.session_state.calendar_year, st.session_state.calendar_month, 1
        )
        st.rerun()
    month_col.markdown(
        f'<div class="calendar-month">{month_names[month]} {year}</div>',
        unsafe_allow_html=True,
    )
    if today_col.button("Hari ini", use_container_width=True):
        st.session_state.calendar_year = today.year
        st.session_state.calendar_month = today.month
        st.session_state.selected_date = today
        st.rerun()
    if next_col.button("→", key="next-month", use_container_width=True):
        st.session_state.calendar_month = 1 if month == 12 else month + 1
        st.session_state.calendar_year = year + 1 if month == 12 else year
        st.session_state.selected_date = date(
            st.session_state.calendar_year, st.session_state.calendar_month, 1
        )
        st.rerun()

    with st.spinner("Menyiapkan kalender..."):
        calendar_tasks = api_request(
            "GET", "/tasks/calendar", params={"year": year, "month": month}
        )
    if calendar_tasks is None:
        st.stop()
    tasks_by_date: dict[date, list[dict]] = {}
    for task in calendar_tasks:
        task_date = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00")).date()
        tasks_by_date.setdefault(task_date, []).append(task)

    month_completed = sum(task["is_completed"] for task in calendar_tasks)
    month_pending = len(calendar_tasks) - month_completed
    scheduled_days = len(tasks_by_date)
    month_stat_columns = st.columns(3)
    month_stat_columns[0].metric("Terjadwal bulan ini", len(calendar_tasks))
    month_stat_columns[1].metric("Belum selesai", month_pending)
    month_stat_columns[2].metric("Hari aktif", scheduled_days)
    st.markdown(
        '<div class="calendar-legend">'
        '<span class="legend-dot dot-selected"></span>Dipilih'
        '<span class="legend-dot dot-task"></span>Memiliki task'
        '<span class="legend-dot dot-today"></span>Hari ini'
        "</div>",
        unsafe_allow_html=True,
    )

    weekday_columns = st.columns(7)
    for column, weekday in zip(
        weekday_columns, ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"], strict=True
    ):
        column.markdown(f'<div class="calendar-weekday">{weekday}</div>', unsafe_allow_html=True)

    for week_index, week in enumerate(Calendar(firstweekday=0).monthdayscalendar(year, month)):
        day_columns = st.columns(7)
        for day_index, day_number in enumerate(week):
            if day_number == 0:
                day_columns[day_index].markdown("&nbsp;", unsafe_allow_html=True)
                continue
            current_date = date(year, month, day_number)
            task_count = len(tasks_by_date.get(current_date, []))
            selected = current_date == st.session_state.selected_date
            if selected:
                marker = "◆"
            elif current_date == today:
                marker = "●"
            elif task_count:
                marker = "•"
            else:
                marker = ""
            label = f"{marker} {day_number}".strip()
            if task_count:
                label += f"  ({task_count})"
            if day_columns[day_index].button(
                label,
                key=f"calendar-{week_index}-{day_number}",
                type="secondary",
                use_container_width=True,
                help=f"{task_count} task" if task_count else "Belum ada task",
            ):
                st.session_state.selected_date = current_date
                st.rerun()

    selected_date = st.session_state.selected_date
    st.markdown(
        f'<div class="selected-date">{selected_date.strftime("%d")} '
        f'{month_names[selected_date.month]} {selected_date.year}</div>',
        unsafe_allow_html=True,
    )
    quick_col, scheduled_col = st.columns([1.15, 1])
    with quick_col:
        with st.container(border=True):
            st.markdown("#### Quick add")
            st.caption("Task akan otomatis dijadwalkan pada tanggal yang dipilih.")
            with st.form(f"calendar-add-{selected_date.isoformat()}", clear_on_submit=True):
                quick_title = st.text_input("Nama task", placeholder="Apa yang perlu dikerjakan?")
                quick_priority = st.selectbox(
                    "Priority", ["medium", "high", "low"], key="calendar-priority"
                )
                quick_description = st.text_area("Catatan", height=80)
                if st.form_submit_button(
                    "Tambahkan ke kalender", type="primary", use_container_width=True
                ):
                    created = api_request(
                        "POST",
                        "/tasks",
                        json={
                            "title": quick_title,
                            "description": quick_description or None,
                            "priority": quick_priority,
                            "due_date": selected_date.isoformat(),
                        },
                    )
                    if created:
                        set_flash("Task ditambahkan ke kalender.")
                        st.rerun()
    with scheduled_col:
        st.markdown("#### Terjadwal")
        selected_tasks = tasks_by_date.get(selected_date, [])
        if not selected_tasks:
            st.caption("Belum ada task pada tanggal ini.")
        for task in selected_tasks:
            with st.container(border=True):
                completed = st.checkbox(
                    task["title"], task["is_completed"], key=f"calendar-done-{task['id']}"
                )
                st.caption(f"Priority {PRIORITY_LABELS[task['priority']]}")
                if completed != task["is_completed"]:
                    if api_request(
                        "PATCH", f"/tasks/{task['id']}", json={"is_completed": completed}
                    ):
                        set_flash("Status task diperbarui.")
                        st.rerun()
    st.stop()

status_map = {"Belum selesai": False, "Selesai": True}
priority_map = {"Tinggi": "high", "Sedang": "medium", "Rendah": "low"}
sort_map = {"Terbaru": "created_at", "Due date": "due_date", "Priority": "priority"}
params = {
    "page": st.session_state.task_page,
    "page_size": 10,
    "overdue": overdue,
    "sort_by": sort_map[sort_label],
    "sort_order": "desc" if sort_direction == "Menurun" else "asc",
}
if status_filter != "Semua":
    params["is_completed"] = status_map[status_filter]
if priority_filter != "Semua":
    params["priority"] = priority_map[priority_filter]
if search:
    params["search"] = search

with st.spinner("Memuat task..."):
    result = api_request("GET", "/tasks", params=params)
if result is None:
    st.stop()
if result["pages"] and st.session_state.task_page > result["pages"]:
    st.session_state.task_page = result["pages"]
    st.rerun()
if not result["pages"] and st.session_state.task_page != 1:
    reset_page()
    st.rerun()

list_title_col, result_col = st.columns([4, 1])
list_title_col.markdown("### Daftar task")
result_col.caption(f"{result['total']} hasil · halaman {result['page']}")


@st.dialog("Hapus task?")
def confirm_delete(task: dict) -> None:
    st.write(f'**{task["title"]}** akan dihapus permanen.')
    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button("Hapus", type="primary", use_container_width=True):
        if api_request("DELETE", f"/tasks/{task['id']}"):
            set_flash("Task berhasil dihapus.")
            st.rerun()
    if cancel_col.button("Batal", use_container_width=True):
        st.rerun()


if not result["items"]:
    st.markdown(
        '<div class="empty-state"><div class="empty-icon">◎</div>'
        '<b>Belum ada task yang cocok</b><br>Ubah filter atau buat task baru.</div>',
        unsafe_allow_html=True,
    )

for task in result["items"]:
    with st.container(border=True):
        check_col, content_col, menu_col = st.columns([0.45, 7, 1.2], vertical_alignment="top")
        completed = check_col.checkbox(
            "Selesai", value=task["is_completed"], key=f"done-{task['id']}",
            label_visibility="collapsed",
        )
        if completed != task["is_completed"]:
            if api_request(
                "PATCH", f"/tasks/{task['id']}", json={"is_completed": completed}
            ):
                set_flash("Status task diperbarui.")
                st.rerun()

        due_label, due_state = format_due_date(task["due_date"], task["is_completed"])
        priority_label = PRIORITY_LABELS[task["priority"]]
        title_class = "task-title done" if task["is_completed"] else "task-title"
        due_class = "badge-overdue" if due_state == "error" else "badge-neutral"
        status_label = "Selesai" if task["is_completed"] else "Aktif"
        content_col.markdown(
            f'<div class="{title_class}">{escape(task["title"])}</div>'
            f'<span class="badge badge-{task["priority"]}">{priority_label}</span>'
            f'<span class="badge {due_class}">{escape(due_label)}</span>'
            f'<span class="badge badge-neutral">{status_label}</span>',
            unsafe_allow_html=True,
        )
        if task["description"]:
            content_col.caption(task["description"])
        if menu_col.button("Hapus", key=f"delete-{task['id']}", use_container_width=True):
            confirm_delete(task)

        with st.expander("Edit detail"):
            with st.form(f"edit-{task['id']}"):
                edited_title = st.text_input("Judul", value=task["title"])
                edited_description = st.text_area(
                    "Deskripsi", value=task["description"] or "", height=80
                )
                edited_priority = st.selectbox(
                    "Priority", ["low", "medium", "high"],
                    index=["low", "medium", "high"].index(task["priority"]),
                )
                if st.form_submit_button("Simpan perubahan", type="primary"):
                    updated = api_request(
                        "PATCH",
                        f"/tasks/{task['id']}",
                        json={
                            "title": edited_title,
                            "description": edited_description or None,
                            "priority": edited_priority,
                        },
                    )
                    if updated:
                        set_flash("Perubahan berhasil disimpan.")
                        st.rerun()

if result["pages"] > 1:
    previous_col, page_col, next_col = st.columns([1, 2, 1])
    if previous_col.button(
        "← Sebelumnya", disabled=result["page"] <= 1, use_container_width=True
    ):
        st.session_state.task_page -= 1
        st.rerun()
    page_col.markdown(
        f"<p style='text-align:center'>Halaman {result['page']} dari {result['pages']}</p>",
        unsafe_allow_html=True,
    )
    if next_col.button(
        "Berikutnya →", disabled=result["page"] >= result["pages"], use_container_width=True
    ):
        st.session_state.task_page += 1
        st.rerun()
