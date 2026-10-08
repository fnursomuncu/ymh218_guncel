# 🚀 Görev Yöneticisi (Full-Stack Task Management)

Bu proje, modern web teknolojileri kullanılarak geliştirilmiş, güvenli ve ölçeklenebilir bir görev yönetim sistemidir. Backend tarafında **FastAPI**, frontend tarafında ise **React 19** ve **Vite 8** kullanılarak hızlı ve akıcı bir kullanıcı deneyimi hedeflenmiştir.

> Veri Yapıları dersi kapsamında grup projesi olarak geliştirilmiştir.

---

## ✨ Öne Çıkan Özellikler

### ⚙️ Backend (Sunucu Tarafı)
* **🔒 Güvenli kimlik doğrulama:** JWT tabanlı oturum yönetimi ve büyük/küçük harf, rakam ve özel karakter zorunluluğu içeren sıkı şifre politikası. Şifreler Bcrypt ile hash'lenerek saklanır.
* **🔄 Veri senkronizasyonu:** Çakışmaları çözmek için **LWW (Last-Write-Wins)** algoritması ve alan bazlı zaman damgaları (`title_updated_at`, `desc_updated_at`). Ayrıntılar için [LWW bölümüne](#-çakışma-çözümü-lww-last-write-wins) bakın.
* **📋 Görev ve yorum sistemi:** Görev oluşturma, güncelleme, silme, öncelik (High / Normal / Low) atama ve görevlere yorum yapabilme.
* **🛡️ Veri doğrulama:** Pydantic v2 ile tüm istek ve yanıtların doğrulanması; FastAPI'nin otomatik OpenAPI (JSON Schema) dokümantasyonu.

### 🎨 Frontend (Arayüz Tarafı)
* **⚡ Hızlı geliştirme ortamı:** React 19 ve Vite 8 ile hızlı derleme ve anında yenilenen geliştirme sunucusu.
* **🖱️ Akıcı kullanım:** İşlemler sonrasında veriler sayfa yenilenmeden güncellenir.
* **🔔 Bildirimler:** `react-hot-toast` ile kullanıcı işlemlerine dair anlık geri bildirimler.
* **🧹 Temiz kod:** ESLint 10 yapılandırması ile tutarlı ve sürdürülebilir kod.

---

## 🧰 Teknoloji Yığını

| Katman | Teknolojiler |
| :--- | :--- |
| **Backend** | Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2, Passlib (Bcrypt), python-jose (JWT) |
| **Frontend** | React 19, Vite 8, JavaScript (ES6+), React Hot Toast, ESLint 10 |
| **Veritabanı** | SQLite |
| **Paket yönetimi** | pip, npm |

---

## 🔄 Çakışma Çözümü: LWW (Last-Write-Wins)

Aynı görev birden fazla kullanıcı tarafından aynı anda düzenlendiğinde hangi değişikliğin geçerli olacağına **Last-Write-Wins** stratejisiyle karar verilir: aynı alan üzerindeki çakışan güncellemelerden **zaman damgası en yeni olan** kazanır.

Zaman damgaları görev bazında değil, **alan bazında** tutulur:

| Alan | Zaman damgası |
| :--- | :--- |
| Başlık (`title`) | `title_updated_at` |
| Açıklama (`description`) | `desc_updated_at` |

Bu sayede bir kullanıcı görevin başlığını, diğeri açıklamasını değiştirdiğinde iki değişiklik de korunur. Biri diğerinin üzerine yazmaz. Yalnızca **aynı alan** üzerinde çakışma olduğunda en son yazılan değer geçerli olur.

---

## 📂 Proje Yapısı

```text
├── backend/
│   ├── main.py             # API uç noktaları ve ana mantık
│   ├── models.py           # Veritabanı tabloları (User, Task, Comment)
│   ├── schemas.py          # Pydantic veri modelleri ve doğrulama
│   ├── security.py         # Şifreleme ve JWT token yönetimi
│   ├── database.py         # Veritabanı bağlantı ayarları
│   ├── requirements.txt    # Python bağımlılıkları
│   └── combine_codes.py    # Proje dosyalarını tek dosyada birleştiren yardımcı script
└── frontend/
    ├── src/
    │   ├── App.jsx         # Ana uygulama bileşeni ve arayüz mantığı
    │   └── main.jsx        # React giriş noktası
    ├── index.html          # Ana HTML dosyası
    ├── package.json        # Bağımlılıklar ve scriptler
    └── vite.config.js      # Vite yapılandırması
```

---

## 🛠️ Kurulum ve Başlatma

Projeyi yerel ortamınızda çalıştırmak için aşağıdaki adımları sırasıyla takip edin.

### Gereksinimler

- Python 3
- Node.js ve npm

### 1. Backend

Proje ana klasöründen başlayarak:

```bash
cd backend

# Sanal ortam oluşturun
python -m venv venv

# Sanal ortamı etkinleştirin
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Sunucuyu başlatın
uvicorn main:app --reload
```

API varsayılan olarak `http://127.0.0.1:8000` adresinde çalışır.
Otomatik oluşturulan etkileşimli API dokümantasyonu: `http://127.0.0.1:8000/docs`

### 2. Frontend

Backend çalışmaya devam ederken **yeni bir terminal** açın ve proje ana klasöründen başlayın:

```bash
cd frontend

# Bağımlılıkları yükleyin
npm install

# Geliştirme sunucusunu başlatın
npm run dev
```

Uygulama varsayılan olarak `http://localhost:5173` adresinde açılır.

---

## 👥 Ekip

<!-- Ekip üyelerinin isimlerini aşağıya ekleyin -->

- Ad Soyad
- Ad Soyad
- Ad Soyad
