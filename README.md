# Asisten Ekonomi Harian

Asisten Ekonomi Harian adalah dashboard pribadi untuk memantau ekonomi Indonesia, pasar dan emas, serta jurnal ekonomi, baik yang menjadi fondasi dalam 20 tahun terakhir maupun yang terbit paling baru. Aplikasi ini berjalan mandiri di peramban tanpa perlu langganan Claude atau layanan berbayar apa pun. Ringkasan harian juga bisa dikirim otomatis ke WhatsApp setiap pagi melalui GitHub Actions yang gratis.

## Isi paket

| File | Fungsi |
|---|---|
| `index.html` | Aplikasi dashboard hasil rakitan (jangan diedit langsung; edit `src/` lalu jalankan `python build.py`) |
| `src/index.template.html`, `src/style.css`, `src/app.js` | Sumber tampilan (tema merah, slider, pembaca jurnal, suara) |
| `data/berita.json` | Berita ekonomi per tema, diperbarui otomatis tiap jam |
| `scripts/ambil_berita.py` + `.github/workflows/berita.yml` | Pengambil berita RSS (CNBC Indonesia, CNN Indonesia, Antara, Detik, Tempo, Republika, Liputan6, Google News, CNBC International) |
| `data/indikator.json` | Angka indikator resmi BI, BPS, dan Kemenkeu yang Anda perbarui setiap ada rilis baru |
| `scripts/kirim_wa.py` | Skrip penyusun dan pengirim ringkasan harian ke WhatsApp |
| `.github/workflows/harian.yml` | Jadwal otomatis setiap hari pukul 06.00 WIT |
| `build.py` | Merakit `index.html` dari folder `src/` |

## Cara 1: Pakai langsung di HP atau laptop (paling cepat)

Buka file `index.html` dengan Chrome. Semua data otomatis (kurs, emas, jurnal, grafik, dan widget pasar) langsung berjalan selama ada koneksi internet. Angka indikator memakai data bawaan, dan Anda bisa memperbaruinya lewat tombol **✎ Perbarui angka** di menu Ekonomi Indonesia. Perubahan tersebut tersimpan di perangkat itu saja.

## Cara 2: Hosting gratis di GitHub Pages dengan kirim WA otomatis (disarankan)

### Langkah A. Unggah ke GitHub

1. Buat akun gratis di github.com.
2. Buat repository baru, misalnya `asisten-ekonomi`, dengan visibilitas **Public** agar GitHub Pages dan Actions sepenuhnya gratis.
3. Klik **Add file → Upload files**, lalu unggah seluruh isi folder ini. Pastikan folder tersembunyi `.github` ikut terunggah. Jika tidak terunggah, buat file `.github/workflows/harian.yml` secara manual melalui **Add file → Create new file**, lalu salin isinya.

### Langkah B. Aktifkan dashboard online

1. Buka **Settings → Pages**.
2. Pada bagian Source, pilih **Deploy from a branch**, lalu pilih branch `main` dan folder `/ (root)`. Klik Save.
3. Setelah sekitar 1–2 menit, dashboard bisa diakses di `https://NAMAAKUN.github.io/asisten-ekonomi/`.
4. Di HP, buka alamat tersebut di Chrome, lalu pilih **⋮ → Tambahkan ke layar utama** agar dashboard tampil seperti aplikasi.

### Langkah C. Siapkan pengiriman WhatsApp (pilih salah satu)

**Pilihan 1: CallMeBot (gratis, untuk mengirim ke nomor sendiri)**

1. Simpan nomor bot CallMeBot ke kontak HP Anda. Nomor terbaru tercantum di callmebot.com, pada halaman *WhatsApp API*.
2. Kirim pesan `I allow callmebot to send me messages` ke nomor tersebut dari WhatsApp Anda.
3. Anda akan menerima balasan berisi **apikey**.

**Pilihan 2: Fonnte (gateway WhatsApp Indonesia)**

1. Daftar di fonnte.com, lalu hubungkan sebuah nomor WhatsApp sebagai pengirim dengan memindai QR code.
2. Salin **token** perangkat tersebut. Paket gratis Fonnte memiliki batas kuota, jadi cek ketentuannya di situs mereka.

### Langkah D. Masukkan kunci ke GitHub

Buka **Settings → Secrets and variables → Actions**.

- Tab **Secrets → New repository secret**:
  - `WA_PHONE` = `62895353066404`
  - `CALLMEBOT_APIKEY` = apikey dari CallMeBot, **atau** `FONNTE_TOKEN` = token dari Fonnte
- Tab **Variables → New repository variable**:
  - `DASHBOARD_URL` = alamat GitHub Pages dari Langkah B

### Langkah E. Uji coba

Buka tab **Actions → Ringkasan ekonomi harian ke WhatsApp → Run workflow**. Dalam satu menit pesan akan masuk ke WhatsApp Anda. Setelah itu, pesan dikirim otomatis setiap hari pukul 06.00 WIT. Untuk mengganti jam pengiriman, ubah baris `cron` di `.github/workflows/harian.yml`. Waktu di sana memakai UTC, jadi 06.00 WIT = 21.00 UTC hari sebelumnya.

## Memperbarui angka indikator resmi

Bank Indonesia, BPS, dan Kemenkeu belum menyediakan API publik gratis yang bisa dibaca langsung oleh peramban. Karena itu, angka seperti BI-Rate, inflasi, PDB, APBN, dan NTP disimpan di `data/indikator.json`. Untuk memperbaruinya:

1. Di GitHub, buka `data/indikator.json` lalu klik ikon pensil (✎).
2. Ubah `nilai`, `periode`, dan `keterangan` sesuai rilis resmi terbaru, lalu ubah juga `diperbarui` ke tanggal hari itu.
3. Klik **Commit changes**. Dashboard dan pesan WhatsApp berikutnya akan langsung memakai angka baru.

Jadwal rilis yang perlu dipantau:

| Data | Penerbit | Jadwal |
|---|---|---|
| Inflasi, NTP, dan neraca perdagangan | BPS | Hari kerja pertama setiap bulan |
| Cadangan devisa | BI | Sekitar tanggal 7 setiap bulan |
| BI-Rate | BI | Setelah Rapat Dewan Gubernur, pertengahan bulan |
| APBN KiTa | Kemenkeu | Pertengahan bulan |
| Pertumbuhan PDB | BPS | Awal Februari, Mei, Agustus, dan November |

Kalender rilis di menu Ekonomi Indonesia menampilkan jadwal ini secara realtime.

## Sumber data otomatis (semua gratis, tanpa kunci API)

| Data | Sumber | Keterangan |
|---|---|---|
| Jurnal | OpenAlex | Jurnal fondasi dipilih dari artikel paling banyak dikutip yang terbit 20 tahun terakhir. Jurnal terbaru diambil dari terbitan 30 hari terakhir. Headline adalah artikel ekonomi yang paling banyak dikutip dalam 12 bulan terakhir. |
| Kurs | Frankfurter | Kurs referensi harian ECB |
| Emas dunia | gold-api.com | Realtime |
| Saham, indeks, komoditas, berita, kalender | Widget TradingView | Realtime atau tertunda, tergantung bursa |
| Tren tahunan | World Bank API | Data tahunan |
| IHSG di pesan WA | Yahoo Finance | Tidak resmi. Jika gagal, bagian IHSG dilewati. |
| Terjemahan ringkasan | Google Translate | Layanan gratis tidak resmi. Jika gagal, teks asli tetap tampil. |

## Fitur tampilan

Dashboard memakai tema merah dan bisa diganti ke mode terang atau gelap lewat ikon bulan/matahari. Berita dan jurnal tampil dalam slider yang bisa digeser ke kiri dan kanan, dan bergerak otomatis. Slider berhenti sebentar saat disentuh dan bisa dijeda.

**Berita** dikelompokkan per tema: Makro, Moneter & Perbankan, Fiskal & Pajak, Pasar & Investasi, Pertanian & Pangan, Energi & Tambang, Syariah, Politik & Kebijakan, dan Global. Berita politik hanya diambil bila menyangkut ekonomi, anggaran, regulasi, atau kebijakan publik. Berita juga bisa disaring per media dan dicari dengan kata kunci.

**Data ekonomi** dikelompokkan dalam tab Makro, Moneter, Fiskal, Pertanian & Mikro, Politik & Kebijakan (isu kebijakan terhangat, indikator tata kelola World Bank, dan tautan regulasi resmi), serta Kalender Rilis. Setiap tab berisi angka indikator, analisis, grafik tren 20 tahun, berita terkait, dan referensi resmi Indonesia.

**Setiap jurnal memiliki tiga kolom analisis:**
- **Informasi** berisi konteks, tujuan, data, metode, dan wilayah kajian.
- **Argumentasi** berisi klaim dan temuan utama penulis.
- **Interpretasi** berisi implikasi dan relevansi, termasuk catatan sitasi dan kaitannya dengan Indonesia.

Kolom-kolom ini disusun otomatis dengan memilah kalimat abstrak menurut perannya. Ketiganya tampil di kartu jurnal, di pembaca, dan di pesan WhatsApp, serta ikut terekspor ke CSV.

**Jurnal dan berita bisa dibaca langsung di dalam aplikasi.** Ketuk sebuah kartu untuk membuka pembaca. Dari pembaca, Anda bisa:
- menerjemahkan isi (Asli / Indonesia / English);
- mendengarkan dalam Bahasa Indonesia atau Inggris;
- menyalin sitasi APA;
- menandai sudah dibaca;
- menyimpan ke Arsip;
- menampilkan PDF untuk artikel akses terbuka.

Untuk berita, pembaca hanya menampilkan ringkasan dari RSS, karena artikel lengkapnya milik media yang bersangkutan.

## Menyesuaikan bidang jurnal

Kata kunci tiap bidang ada di bagian `BIDANG`, yaitu di `src/app.js` (untuk dashboard) dan di `scripts/kirim_wa.py` (untuk WhatsApp). Contohnya `agricultural` untuk ekonomi pertanian dan `islamic` untuk ekonomi syariah. Ganti kata kunci sesuai minat Anda. Setelah mengubah template, jalankan `python build.py`.

## Catatan penting

- Ringkasan jurnal diambil dari kalimat pertama abstrak, bukan ditulis ulang oleh AI. Bagian "Mengapa masih relevan" dihitung dari data sitasi.
- Analisis ekonomi harian disusun dengan aturan baku. Contohnya: inflasi dibandingkan dengan sasaran BI 2,5±1%, suku bunga riil dihitung dari BI-Rate dikurangi inflasi, defisit dibandingkan dengan batas 3% PDB, dan NTP dibandingkan dengan angka 100.
- Jika ada simbol di widget TradingView yang bertuliskan "hanya tersedia di TradingView", ganti simbol tersebut di bagian `TV` pada `src/app.js`.
- Jika salah satu media berita tidak muncul, cek statusnya di halaman Berita, bagian "Sumber berita & status", lalu ganti alamat RSS-nya di `scripts/ambil_berita.py`.
- Seluruh informasi bersifat edukatif dan bukan rekomendasi investasi.
