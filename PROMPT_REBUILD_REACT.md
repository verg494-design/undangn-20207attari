# PROMPT: Rebuild ATTARIVITATION menjadi React yang benar

Salin seluruh isi di bawah ini ke AI coding agent (Claude Code / Cursor / Copilot Agent / dll).

---

## KONTEKS PROYEK

Kamu bekerja pada proyek **Windows** di `D:\ATTARIVITATION_REACT_FINAL`.

Ini adalah hasil migrasi situs undangan pernikahan WordPress/Elementor menjadi React. Kondisi saat ini **belum berfungsi**:

- `src/App.jsx` hanya me-route `/` → `HomePage` (placeholder 0,3 KB).
- Ada 83 file di `src/pages/invitations/*.jsx` hasil konversi HTML otomatis yang **rusak** (bug `elements` undefined, tag mismatch, `src={""}`, 5194 URL absolut ke `byattari.com`, `<script>` di dalam JSX, CSS selector jadi teks).
- 83 halaman itu **tidak pernah di-import** oleh App.
- Styling per halaman tidak terhubung.
- Repo menyimpan ±1 GB aset termasuk folder `archive/` duplikat.

**Tugasmu: rebuild aplikasi ini dari nol menggunakan file HTML backup sebagai sumber kebenaran (source of truth), bukan memakai JSX lama yang rusak.**

---

## SUMBER DATA (WAJIB DIBACA DARI SINI)

### Template HTML asli (jangan diubah, hanya dibaca)
```
D:\ATTARIVITATION_BACKUP\ATTARIVITATION_FULL_BACKUP\pages\
├── index.html                     ← homepage
├── adhe-abby\index.html
├── adiesti-azka\index.html
├── alma-haris\index_*.html        ← beberapa varian (komentar), pilih satu
├── ...
└── zicki-nabila\index.html        ← total 77 folder slug
```

### Aset asli
```
D:\ATTARIVITATION_BACKUP\ATTARIVITATION_FULL_BACKUP\
├── css\      (283 file)
├── js\       (128 file)
├── fonts\    (1706 file)
├── images\   (3298 file)
└── videos\   (71 file)
```

### Proyek target
```
D:\ATTARIVITATION_REACT_FINAL\
├── src\
│   ├── main.jsx
│   ├── App.jsx
│   ├── components\
│   ├── layouts\
│   ├── pages\
│   ├── data\          ← BUAT BARU
│   ├── hooks\         ← BUAT BARU
│   └── styles\
├── public\assets\
├── index.html
├── package.json
└── vite.config.js
```

Stack yang dipakai: **React 18 + Vite 5 + React Router 6** (sudah terpasang). Jangan ganti stack. Jangan tambah dependency berat kecuali benar-benar perlu.

---

## ATURAN KERAS (JANGAN DILANGGAR)

1. **JANGAN memakai ulang** file di `src/pages/invitations/*.jsx` yang ada sekarang. File itu boleh dihapus/diarsipkan setelah digantikan. Regenerasi dari HTML.
2. **JANGAN mengubah atau menghapus** folder `D:\ATTARIVITATION_BACKUP`. Folder itu read-only.
3. **Tidak boleh ada** di dalam komponen React:
   - `<script>` atau `<link rel="stylesheet">` di dalam JSX
   - `class=` (harus `className=`), `for=`, `tabindex=`, atribut HTML non-camelCase
   - komentar HTML `<!-- -->`
   - teks CSS selector nyasar seperti `.cui-comment`, `.cui-wrap-comments`
   - selector CSS yang tertulis sebagai teks konten
   - `style="..."` string (harus object `style={{ }}`)
   - tag yang tidak tertutup / double closing tag
   - variabel tak terdefinisi (contoh nyata di kode lama: `elements.forEach(...)` di cleanup `useEffect` — `elements` tidak pernah dideklarasikan)
4. **Tidak boleh ada URL absolut** ke domain asli. Semua `https://attarivitation.com/...` dan `https://byattari.com/...` **wajib ditulis ulang** ke path lokal.
5. **Tidak boleh ada gambar kosong** (`src={""}`) atau `href={""}`.
6. Semua teks yang mengandung `<`, `>`, `&` harus di-escape dengan benar.
7. Bangun **satu template reusable**, bukan 77 salinan markup. Konten per undangan dipisah ke data file.
8. Semua halaman **wajib lazy-loaded** (`React.lazy` + `Suspense`). Bundle awal harus tetap kecil.
9. Harus **berjalan offline**: tidak boleh bergantung pada CDN atau domain lama untuk gambar, font, CSS, audio, video.
10. Jangan commit `node_modules/`, `dist/`, `.env`.

---

## LANGKAH KERJA

### Langkah 1 — Bersihkan proyek
- Hapus 6 file `src/pages/invitations/VenvLibSitePackagesPlaywright...*.jsx` (artefak Python venv, bukan halaman).
- Hapus script proses konversi di root: `create_full_routes.py`, `fix_all_css_selectors.py`, `fix_css_selectors.py`, `fix_text_content.py`, `test_individual_files.py`, `validate_all_jsx.py`, dan file `*_REPORT.*`, `*_AUDIT.*`, `FILES_FAILED.json`, `ROUTE_MAP*.json`, `CONVERSION_REPORT.json`, `AUDIT_REPORT.json`.
- Hapus folder duplikat `public/assets/archive/` (±910 MB) **setelah** memastikan aset yang dipakai sudah dipindahkan ke folder bersih.
- Sisakan struktur aset final:
  ```
  public/assets/images/...
  public/assets/css/...
  public/assets/js/...
  public/assets/fonts/...
  public/assets/videos/...
  public/assets/audio/...
  ```

### Langkah 2 — Inventaris template
- Baca seluruh `index.html` di `D:\ATTARIVITATION_BACKUP\ATTARIVITATION_FULL_BACKUP\pages\`.
- Buat `src/data/routes.js` berisi daftar `{ slug, name, template }` dari nama folder.
  - `adhe-abby` → route `/adhe-abby`
  - `demo-premium-01` → route `/demo-premium-01`
  - `portfolio-attari` → route `/portfolio`
- Kelompokkan halaman berdasarkan **struktur visual**, bukan nama. Identifikasi template induk, misalnya: `classic`, `heritage`, `moody`, `premium`, `sage`, `papercut`, `wave`, `video`, `frame`.
- Tulis hasil inventaris di `src/data/templates.md` (ringkas: slug → template + ciri khas).

### Langkah 3 — Ekstrak aset & rewrite URL
- Copy aset dari backup ke `public/assets/` dengan struktur yang dipertahankan.
- Buat **satu script Node** (`scripts/localize-assets.mjs`) yang:
  1. Memindai semua HTML di backup, mengumpulkan setiap URL `https://attarivitation.com/...` / `https://byattari.com/...`.
  2. Menyalin file terkait ke `public/assets/<path>`.
  3. Menghasilkan peta rewrite, contoh:
     ```
     https://attarivitation.com/wp-content/uploads/2024/10/foto.webp
       → /assets/images/wp-content/uploads/2024/10/foto.webp

     https://attarivitation.com/wp-content/plugins/elementor/assets/css/frontend.css
       → /assets/css/wp-content/plugins/elementor/assets/css/frontend.css
     ```
  4. Melaporkan URL yang filenya tidak ditemukan ke `scripts/missing-assets.json`.
- Jalankan script, lalu verifikasi **0 URL absolut** tersisa di output komponen.

### Langkah 4 — Desain ulang struktur komponen
Pecah setiap template menjadi komponen bermakna (bukan satu file 400 KB):

```
src/
├── components/
│   ├── layout/
│   │   ├── InvitationLayout.jsx     ← wrapper + theme
│   │   ├── Cover.jsx                ← layar pembuka "Open Invitation"
│   │   ├── BottomNav.jsx
│   │   └── MusicPlayer.jsx
│   ├── sections/
│   │   ├── HeroSection.jsx
│   │   ├── CoupleSection.jsx
│   │   ├── CountdownSection.jsx
│   │   ├── EventSection.jsx
│   │   ├── GallerySection.jsx
│   │   ├── LoveStorySection.jsx
│   │   ├── GiftSection.jsx
│   │   ├── RsvpSection.jsx
│   │   ├── GuestbookSection.jsx
│   │   └── ClosingSection.jsx
│   └── common/
│       ├── Header.jsx
│       ├── Footer.jsx
│       └── ...
├── hooks/
│   ├── useCountdown.js
│   ├── useMusic.js
│   ├── useScrollReveal.js
│   └── useLocalStorage.js
├── data/
│   ├── routes.js
│   ├── invitations/
│   │   ├── zicki-nabila.js
│   │   ├── adhe-abby.js
│   │   └── ...
│   └── templates.md
├── pages/
│   ├── HomePage.jsx
│   ├── PortfolioPage.jsx
│   ├── NotFoundPage.jsx
│   └── InvitationPage.jsx           ← render berdasarkan slug
└── styles/
    ├── global/index.css
    ├── themes/*.css
    └── sections/*.css
```

Skema data per undangan:
```js
// src/data/invitations/zicki-nabila.js
export default {
  slug: 'zicki-nabila',
  template: 'heritage',            // pilih salah satu template
  meta: {
    title: 'Zicki & Nabila',
    description: '...',
    ogImage: '/assets/images/wp-content/uploads/2024/10/cover.webp',
  },
  cover: {
    label: 'The Wedding Of',
    headline: 'Zicki & Nabila',
    date: '2024-09-23T08:00:00+07:00',
    backgroundVideo: 'https://www.youtube.com/embed/hI7ezmqw_4U',
  },
  couple: {
    groom: { name: 'Zicki', parents: '...', photo: '/assets/...' },
    bride: { name: 'Nabila', parents: '...', photo: '/assets/...' },
  },
  events: [
    { name: 'Akad Nikah', date: '2024-09-23T08:00:00+07:00', place: '...', mapUrl: '...' },
    { name: 'Resepsi',   date: '2024-09-23T11:00:00+07:00', place: '...', mapUrl: '...' },
  ],
  gallery: ['/assets/...'],
  gift: { accounts: [{ bank: 'BCA', number: '...', holder: '...' }], address: '...' },
  music: '/assets/audio/zicki-nabila.mp3',
}
```

### Langkah 5 — Implementasi perilaku interaktif
Reimplementasikan fungsi Elementor yang hilang dengan React murni:

| Fitur | Implementasi |
|---|---|
| Countdown | `useCountdown` + `setInterval`, bersihkan di cleanup |
| Cover "Open Invitation" | state + disable scroll body selama cover tampil |
| Background music | `<audio>` ref, toggle play/pause, autoplay setelah interaksi user |
| Scroll reveal | `IntersectionObserver` di `useScrollReveal` |
| Gallery lightbox | state modal, keyboard `Esc`, focus trap |
| RSVP / Guestbook | form React terkontrol + validasi; simpan ke `localStorage` (atau mock API) |
| Copy rekening | `navigator.clipboard.writeText` + toast |
| Google Maps | `<iframe>` dengan `loading="lazy"` tetap diizinkan |
| YouTube hero | `<iframe>` dengan `loading="lazy"` + `title` |
| Tombol share | `navigator.share` dengan fallback copy link |

Setiap `useEffect` **wajib** punya cleanup yang valid dan tidak mereferensikan variabel yang tidak ada.

### Langkah 6 — Routing
`src/App.jsx`:
```jsx
const InvitationPage = React.lazy(() => import('./pages/InvitationPage'))
const HomePage       = React.lazy(() => import('./pages/HomePage'))
const PortfolioPage  = React.lazy(() => import('./pages/PortfolioPage'))
const NotFoundPage   = React.lazy(() => import('./pages/NotFoundPage'))

<BrowserRouter>
  <Suspense fallback={<LoadingScreen />}>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/portfolio" element={<PortfolioPage />} />
      <Route path="/:slug" element={<InvitationPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </Suspense>
</BrowserRouter>
```
`InvitationPage` mengambil `slug` dari `useParams()`, mencocokkan ke `routes.js`, lalu me-render template yang sesuai. Slug tidak dikenal → `NotFoundPage`.

### Langkah 7 — Styling
- Import CSS per template/section secara lokal (`import './CountdownSection.css'`), **bukan** load 40–80 file dari CDN.
- Audit CSS dari backup: buang yang tidak terpakai, pertahankan yang memengaruhi tampilan.
- Hasil visual harus **mirip dengan HTML asli** (layout, warna, font, animasi).
- Wajib responsif: 360px (mobile), 768px (tablet), 1440px (desktop).
- Gunakan font lokal dari `public/assets/fonts` via `@font-face`.

### Langkah 8 — Performa
- `loading="lazy"` + `decoding="async"` untuk semua gambar non-hero.
- `React.lazy` untuk setiap route.
- Hindari import gambar lewat bundler jika ukurannya besar; gunakan path `public/`.
- Target: bundle JS awal < 300 kB (gzip), tidak ada layout shift besar.

---

## VERIFIKASI & DEFINITION OF DONE

Jalankan dan pastikan semuanya lolos:

```bash
npm install
npm run build
npm run dev
```

Checklist:
- [ ] `npm run build` sukses tanpa error.
- [ ] `npm run dev` jalan di `http://localhost:3000`.
- [ ] Homepage tampil (bukan placeholder "Welcome to Attarivitation").
- [ ] Minimal 5 halaman undangan bisa dibuka lewat URL dan tampil benar.
- [ ] Semua 77 slug mengembalikan halaman (tidak blank / tidak crash).
- [ ] Tidak ada error di console browser.
- [ ] Tidak ada request gagal (404) di tab Network.
- [ ] Tidak ada URL `attarivitation.com` / `byattari.com` tersisa di `src/`.
- [ ] Tidak ada `src={""}`.
- [ ] Tidak ada `<script>` di dalam komponen.
- [ ] Gambar, font, audio, video tampil **tanpa internet**.
- [ ] Countdown, musik, galeri, RSVP, guestbook berfungsi.
- [ ] Route `/slug-ngawur` menampilkan halaman 404.
- [ ] Tampilan responsif di 360 / 768 / 1440 px.
- [ ] Ukuran repo turun drastis (tanpa `archive/`).

---

## CARA KERJA YANG DIHARAPKAN

1. **Mulai dari audit**: baca beberapa HTML template (minimal 3 yang berbeda gaya) dan laporkan struktur yang kamu temukan sebelum menulis kode.
2. **Kerjakan bertahap** dan commit tiap fase:
   - `chore: cleanup project`
   - `feat: localize assets + rewrite URLs`
   - `feat: add data schema and route map`
   - `feat: build reusable invitation template`
   - `feat: migrate N invitations`
   - `feat: implement interactive features`
   - `style: theme polishing`
   - `perf: lazy loading and image optimization`
3. **Jangan menebak** isi konten undangan — ambil dari HTML backup.
4. Jika ada keputusan desain yang ambigu (misal memilih 1 dari beberapa varian HTML), **tanya dulu** sebelum lanjut.
5. Setelah selesai, laporkan: daftar route, template yang dibuat, fitur yang berfungsi, dan sisa pekerjaan (jika ada).
