# 🚀 Görev Yöneticisi (Full-Stack Task Management)

Bu proje, modern web teknolojileri kullanılarak geliştirilmiş, güvenli ve ölçeklenebilir bir görev yönetim sistemidir. Backend tarafında **FastAPI**'nin hızı, frontend tarafında ise **React 19** ve **Vite 8**'in güncelliği bir araya getirilerek yüksek performanslı bir kullanıcı deneyimi hedeflenmiştir.

---

## ✨ Öne Çıkan Özellikler

### 🛠️ Backend (Sunucu Tarafı)
* **🔒 Gelişmiş Güvenlik:** JWT tabanlı kimlik doğrulama ve büyük/küçük harf, rakam, özel karakter zorunluluğu içeren sıkı şifre politikası (Security-First).
* **🔄 Veri Senkronizasyonu:** Çakışmaları yönetmek için **LWW (Last-Write-Wins)** algoritması ve alan bazlı zaman damgaları (`title_updated_at`, `desc_updated_at`).
* **📋 Görev & Yorum Sistemi:** Görev oluşturma, güncelleme, silme, öncelik (High/Normal/Low) atama ve görevlere yorum yapabilme desteği.
* **🛡️ Veri Doğrulaması:** Pydantic v2 ve JSON Schema ile hem uygulama seviyesinde hem de veri tabanı seviyesinde tam uyumluluk.

### 🎨 Frontend (Arayüz Tarafı)
* **🚀 Modern Stack:** React 19 ve Vite 8 kullanılarak en güncel ekosistem avantajları.
* **⚡ Hızlı ve Akıcı:** Sayfa yenilemeden anlık veri güncellemeleri ve optimize edilmiş derleme süreci.
* **🔔 Bildirim Yönetimi:** `react-hot-toast` ile kullanıcı işlemlerine dair şık ve etkileşimli geri bildirimler.
* **🛠️ Temiz Kod:** ESLint 10 yapılandırması ile standartlara uygun, sürdürülebilir kod mimarisi.

---

## 🛠️ Teknoloji Yığını

| Katman | Teknolojiler |
| :--- | :--- |
| **Backend** | Python, FastAPI, SQLAlchemy, Pydantic v2, Passlib (Bcrypt), Jose (JWT) |
| **Frontend** | React 19, Vite 8, JavaScript (ES6+), React Hot Toast, ESLint 10 |
| **Veritabanı**| SQLite (Geliştirme süreci için optimize edilmiş) |
| **Araçlar** | Master Code Combiner (Python), Uvicorn, NPM |

---

## 📂 Proje Yapısı

```text
├── backend/
│   ├── main.py            # API uç noktaları ve ana mantık
│   ├── models.py          # Veritabanı tabloları (User, Task, Comment)
│   ├── schemas.py         # Pydantic veri modelleri ve doğrulama
│   ├── security.py        # Şifreleme ve JWT token yönetimi
│   ├── database.py        # DB bağlantı ayarları
│   └── combine_codes.py   # Proje dosyalarını birleştiren yardımcı script
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Ana uygulama bileşeni ve UI mantığı
│   │   └── main.jsx       # React giriş noktası
│   ├── index.html         # Ana HTML dosyası
│   ├── package.json       # Bağımlılıklar ve scriptler
│   └── vite.config.js     # Vite yapılandırması
```

## 🚀 Kurulum ve Başlatma

Projenin yerel ortamınızda çalışması için aşağıdaki adımları sırasıyla takip edin.

### 1. Backend Kurulumu

Backend dizinine gidin ve gerekli bağımlılıkları yükleyin:

```bash
# Klasöre giriş yapın
cd backend

# Python sanal ortamını oluşturun
python -m venv venv

# Sanal ortamı aktif edin
# Windows için:
venv\Scripts\activate
# macOS/Linux için:
source venv/bin/activate

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

## Sunucuyu Başlatma
uvicorn main:app --reload

### 2. Frontend Kurulumu
# Klasöre giriş yapın
cd frontend

# Bağımlılıkları yükleyin (NPM veya Yarn)
npm install

## Uygulama Başlatma
# Geliştirme sunucusunu çalıştırın
npm run dev
