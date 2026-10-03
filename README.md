# Multi-user To-Do API

REST API To-Do List multi-user dengan FastAPI, PostgreSQL, Redis, JWT, repository pattern,
dan service layer. Setiap query task selalu dibatasi oleh user yang terautentikasi.

## Menjalankan dengan Docker

1. Salin `.env.example` menjadi `.env`, lalu ganti `JWT_SECRET` dengan nilai acak minimal
   32 karakter dan `POSTGRES_PASSWORD` dengan password database yang kuat. Nilai placeholder
   JWT/default akan ditolak saat startup.
2. Jalankan:

```bash
docker compose up --build
```

Service API dan GUI menggunakan satu image yang sama agar dependensi tidak dibangun dua kali. Jika
koneksi ke Python package index lambat, proses build otomatis mencoba kembali dengan timeout yang
lebih panjang.

Jika build pertama terhenti karena koneksi, jalankan kembali perintah yang sama. BuildKit akan memakai
cache paket yang sudah selesai diunduh:

```bash
docker compose build app
docker compose up
```

Migration Alembic dijalankan otomatis sebelum API dimulai. Preview GUI Streamlit tersedia di
`http://localhost:8501`, dokumentasi API di `http://localhost:8000/docs`, dan health check di
`http://localhost:8000/health`.

## Endpoint

| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/auth/register` | Registrasi user |
| POST | `/auth/login` | Login dan memperoleh access token |
| GET | `/auth/me` | Profil user aktif |
| GET | `/tasks` | Daftar task dengan pagination/filter/search |
| POST | `/tasks` | Membuat task |
| GET | `/tasks/{id}` | Detail task |
| PATCH | `/tasks/{id}` | Mengubah task termasuk status |
| DELETE | `/tasks/{id}` | Menghapus task |

Gunakan header berikut pada endpoint terproteksi:

```text
Authorization: Bearer <access_token>
```

Contoh daftar task:

```text
GET /tasks?page=1&page_size=20&is_completed=false&priority=high&search=laporan&overdue=false&sort_by=due_date&sort_order=asc
```

Nilai `sort_by` yang tersedia adalah `created_at`, `due_date`, dan `priority`. Gunakan
`overdue=true` untuk hanya menampilkan task belum selesai yang due date-nya sudah lewat.

## Contoh request

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"rahasia-sangat-kuat"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"rahasia-sangat-kuat"}'
```

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Selesaikan laporan","priority":"high","due_date":"2026-10-10T17:00:00+07:00"}'
```

## Cache dan invalidation

- Detail: `task:{user_id}:{task_id}`, TTL default 5 menit.
- Daftar: `tasks:{user_id}:{hash_query}`, TTL default 60 detik.
- Key daftar milik user dicatat pada Redis Set `task-list-keys:{user_id}`.
- Cache miss membaca PostgreSQL lalu mengisi Redis.
- Create menghapus seluruh cache daftar user.
- Update/delete menghapus cache detail dan seluruh cache daftar user.
- Kegagalan Redis tidak mematikan operasi database; request berjalan tanpa cache.

Rate limiting memakai counter atomic Redis per jendela waktu. Default endpoint auth 10 request/menit
per alamat email (disimpan sebagai hash di Redis) dan endpoint task 300 request/menit per user. Nilai
dapat diubah melalui environment variables. Rate limit per akun menghindari semua pengguna Streamlit
berbagi satu limit berdasarkan IP container GUI.

## Struktur

```text
app/
├── main.py
├── config.py
├── security.py
├── dependencies.py
├── routes/
├── models/
├── schemas/
├── services/
├── repositories/
├── database/
└── cache/
streamlit_app.py
```

Route menangani HTTP, service menangani aturan bisnis dan cache, sedangkan repository menjadi satu-satunya
lapisan yang melakukan query database.

## Pengembangan lokal

Membutuhkan Python 3.11+, PostgreSQL, dan Redis.

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Sesuaikan host pada `DATABASE_URL` dan `REDIS_URL` menjadi `localhost` saat API dijalankan di luar Docker.

## Testing dan lint

```bash
pytest
ruff check .
```

Test dasar mencakup password hashing, JWT, health endpoint, ownership user, cache hit/miss,
cache invalidation, serta penerusan filter dan sorting ke repository.
