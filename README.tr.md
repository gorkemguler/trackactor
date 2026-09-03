<p align="center">
  <img src="docs/banner.png" alt="trackactor" width="960">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/UI-React%20%2B%20TS-3178C6?logo=react&logoColor=white" alt="React + TypeScript">
  <img src="https://img.shields.io/badge/lisans-MIT-blue" alt="MIT lisansı">
  <img src="https://img.shields.io/badge/durum-akt%C4%B1f%20geli%C5%9Ftirme-brightgreen" alt="Aktif geliştirme">
</p>

<p align="center"><a href="README.md">English</a> · <b>Türkçe</b></p>

# trackactor

Bir tehdit aktörüyle hangi vaka üzerinden konuştuğunu takip et.

## Problem

İstihbarat platformundan ya da SOC araçlarından bir vaka düşer. Aktöre ulaşırsın:
forum mesajı, bir Telegram hesabı, bir XMPP adresi, bir pazar yeri sohbeti.
Birkaç gün sonra `@bir_kullanici` üzerinden bir yanıt gelir ve bunun hangi vakaya
ait olduğunu hatırlamazsın; çünkü o sırada üç ayrı aktörle dört ayrı yazışma
yürütüyorsundur.

trackactor bunu çözer. Yaptığın teması, sahip olduğun vaka ID'sine baştan
bağlarsın. Yanıt geldiğinde kullanıcı adını veya bağlantıyı arama kutusuna
yapıştırırsın; vakayı, aktörü, bağlı kanalları ve o ana kadarki yazışmayı geri
alırsın.

CTI ekipleri, SOC / SOME analistleri ve aktör temasını kayıt altında tutması
gereken herkes için. İşine kendi araçlarınla entegre edebilmen için bir REST API
de var.

## Ekran görüntüleri

**Panel** — duruma göre açık vakalar ve yeni gelen yanıtlar.

![Panel](docs/screenshots/dashboard.png)

**Ters arama (reverse lookup)** — işin özü. `https://t.me/n3tw0rm_deals`,
`@n3tw0rm_deals` ve `tg://resolve?domain=n3tw0rm_deals` aynı anahtara normalize
olur ve aynı vakaya çıkar.

![Ters arama](docs/screenshots/lookup.png)

**Vakalar** — platformunun zaten verdiği ID ile anahtarlanmış her tema.

![Vakalar](docs/screenshots/cases.png)

**Vaka detayı** — bağlı aktörler ve kanallar, ayrıca gelen/giden mesaj kaydı.

![Vaka detayı](docs/screenshots/case-detail.png)

## Parçalar nasıl birleşiyor

- **Case (Vaka)** — takip edilen bir tema; dış `case_id`'niz ve kaynak
  platformuyla (OpenCTI, MISP, TheHive, Splunk ES, Intel 471, ...) anahtarlanır.
- **Actor (Aktör)** — bir tehdit aktörü, grubu veya personası; takma adlar ve TLP
  etiketiyle.
- **Contact (İletişim kimliği)** — bir aktöre ait tek bir iletişim tanımlayıcısı;
  `t.me/x`, `@x` ve `tg://resolve?domain=x` eşleşsin diye normalize edilmiş
  biçimiyle saklanır.
- **Interaction (Etkileşim)** — bir vakaya işlenmiş gelen ya da giden bir mesaj.

Bir vaka bir veya daha fazla aktöre ve/veya doğrudan belirli iletişim
kimliklerine bağlanır; böylece kimlik henüz bir aktöre atfedilmemiş olsa bile
yanıt yine de vakaya çözülür. `awaiting_response` durumundaki bir vakaya gelen
bir mesaj işlediğinde durum kendiliğinden `responded` olur.

## Çalıştırma

### Docker

```bash
docker compose up -d --build
```

http://localhost:8080 adresini aç. API `/api` altından proxy'lenir, dokümanlar
http://localhost:8080/api/docs adresinde. SQLite veritabanı `trackactor-data`
volume'unda tutulur.

Örnek veriyi yükle (opsiyonel):

```bash
docker compose exec backend python -m app.seed
```

### Yerel

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # opsiyonel örnek veri
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Geliştirme sunucusu http://localhost:5173 adresinde çalışır ve `/api`'yi 8000
portuna proxy'ler.

## API

Kimlik doğrulama yok. Her şey `/api` altında; tam şema `/api/docs` adresinde.

```bash
# vaka oluştur
curl -X POST localhost:8000/api/cases -H 'content-type: application/json' -d '{
  "case_id": "OPENCTI-2026-0042",
  "title": "LockBit affiliate outreach",
  "source_platform": "OpenCTI",
  "status": "awaiting_response"
}'

# yanıt geldi - bu hangi vaka?
curl 'localhost:8000/api/lookup?q=https://t.me/n3tw0rm_deals'
```

| Metod | Yol | Amaç |
| --- | --- | --- |
| `GET` | `/api/lookup?q=` | kullanıcı adı / bağlantı / takma ad / vaka id'sini vaka(lar)a çöz |
| `POST` | `/api/capture` | tek çağrıda vaka + aktör + iletişim kimliği + mesaj oluştur/güncelle ve bağla |
| `GET` `POST` | `/api/cases` | vakaları listele / oluştur |
| `GET` `PATCH` `DELETE` | `/api/cases/{id}` | aktörleri, kimlikleri ve kaydıyla tek vaka |
| `POST` | `/api/cases/{id}/links` | bir aktörü veya iletişim kimliğini vakaya bağla |
| `POST` | `/api/cases/{id}/interactions` | bir mesaj işle |
| `GET` `POST` | `/api/actors` | aktörler ve takma adları |
| `POST` | `/api/actors/{id}/contacts` | bir aktöre kanal ekle |
| `GET` `POST` | `/api/contacts` | iletişim kimliklerinde ara |
| `GET` | `/api/stats` | panel sayaçları |

## Tarayıcı eklentisi

`extension/` klasörü Chrome / Edge / Firefox için paketlenmemiş bir MV3
eklentisi. Bir CTI platformu sayfasındaki vaka ID'sini ya da açık olan Telegram
Web sohbetinin `@handle`'ını alıp, sayfadan çıkmadan `/api/capture` üzerinden bir
vakaya işler. Bkz. [extension/README.md](extension/README.md).

| Yakala | Bağlandı | Ters arama |
| --- | --- | --- |
| ![Eklenti yakalama formu](docs/screenshots/ext-capture.png) | ![Vakaya bağlandı](docs/screenshots/ext-result.png) | ![Popup'ta ters arama](docs/screenshots/ext-lookup.png) |

## Yapılandırma

`backend/.env` ya da doğrudan ortam değişkenleri:

- `TRACKACTOR_DB_URL` — SQLAlchemy URL'i, varsayılan `sqlite:///./trackactor.db`
- `TRACKACTOR_CORS_ORIGINS` — yerel geliştirmede API'yi çağırmasına izin verilen origin'ler (virgülle ayrılmış)

## Teknoloji

Backend'de FastAPI, SQLAlchemy ve SQLite; frontend'de React, TypeScript ve Vite.
Backend testleri: `cd backend && pytest`.

## Notlar

- Kimlik doğrulama yok. İç ağda ya da kendi auth proxy'nin arkasında çalıştır.
- SQLite bir ekip için yeterli. Büyürsen `TRACKACTOR_DB_URL`'i Postgres'e yönlendir.

## Lisans

MIT
