# Market Compass

[Buka dashboard](https://mosses-ai.github.io/market-compass/)

Monitor pasar dan laporan portofolio berbahasa Indonesia, diterbitkan di GitHub Pages. Tidak membutuhkan langganan ChatGPT, API AI, atau API key berbayar. Pengunjung tidak perlu masuk ke akun.

## Pembaruan otomatis

- IHSG, watchlist BBCA/BBRI/BMRI/ARTO/HRTA/TLKM dan top gainers/losers: **widget resmi TradingView untuk IDX, EOD (akhir hari)**. Data ini bukan streaming real-time IDX. Hari libur memakai sesi terakhir. Ketersediaan dan waktu data mengikuti widget.
- Emas spot XAU/USD (USD per troy ounce), USD/SGD/CHF terhadap IDR, dan Brent: feed pasar penyedia di dalam widget. Ini berbeda dari kuotasi transaksi bank dan emas retail.
- Monitor PESTLE/geopolitik: judul + waktu publikasi + tautan dari sepuluh RSS resmi ANTARA. Dikelompokkan menurut rubrik penerbit; feed terkini ditambah tag kata judul yang transparan dan dapat keliru. Ini bukan analisis risiko, sentimen, atau rekomendasi yang dibuat otomatis.
- GitHub Actions memeriksa RSS setiap jam pada menit 17 UTC (menit 17 juga di WIB) dan menerbitkan `data/live.json`. Jadwal dapat tertunda. Halaman terbuka mengecek hasil setiap lima menit, atau melalui tombol muat ulang.
- Jika feed gagal, judul dan waktu keberhasilan terakhir dipertahankan. Sumber gagal atau pemeriksaan berusia lebih dari tiga jam ditandai. Waktu pemeriksaan server berbeda dari waktu publikasi artikel dan waktu kuotasi.

**Batas yang tetap manual:** kuotasi beli/jual HRTA GOLD Livin', bid/ask Poket Valas myBCA, biaya/promo aktual dan NAB RDPU. Tidak mengakses rekening atau broker.

Bagian kajian, alokasi, pola historis, aturan timing dan skenario tetap **snapshot 22 Oktober 2026**, dengan horizon 22 Januari 2027. Feed tidak menimpa harga jangkar atau menghitung ulang kesimpulan tersebut. Spread HRTA 2% tetap asumsi sampai pengguna mengisi kuotasi aplikasi. Simulasi bukan prediksi pasti. Isian hanya dihitung di browser dan kembali ke nilai awal saat halaman dimuat ulang.

## Pengoperasian

Pages memakai **GitHub Actions** sebagai sumber, dengan workflow `Refresh news and publish dashboard`. Tidak ada secrets tambahan. Hak token: baca kode, serta Pages + OIDC untuk deployment. File publik dibatasi ke `index.html`, `live.css`, `live.js`, `.nojekyll` dan `data/live.json`.

GitHub dapat menonaktifkan jadwal repositori publik setelah 60 hari tanpa aktivitas repositori. Jika status berita menua: buka **Actions → Refresh news and publish dashboard**, aktifkan kembali jika dinonaktifkan, lalu **Run workflow** pada `main`. Widget pasar tetap bergantung pada penyedia. Perubahan kebijakan/kuota layanan gratis dapat memerlukan pemeliharaan.

Untuk memeriksa atau membangun lokal (Python 3, tanpa paket tambahan):

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/update_news.py
python3 scripts/build.py
```

Folder `_site/` adalah keluaran publik. Laporan dan kalkulator lama tersedia offline dalam HTML; monitor eksternal dan pemuatan JSON membutuhkan koneksi/HTTP.

## Sumber dan lisensi data

- [Cakupan data widget TradingView](https://www.tradingview.com/widget-docs/markets/asia-pacific/): IDX EOD untuk saham dan indeks.
- [FAQ data widget](https://www.tradingview.com/widget-docs/faq/data/): paket pribadi TradingView tidak meningkatkan hak data widget situs.
- [Direktori RSS resmi ANTARA](https://www.antaranews.com/rss/): atribusi dan tautan dipertahankan; isi artikel penuh tidak disalin.
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

Widget resmi mempertahankan atribusi penyedia. Kegagalan widget tidak diganti dengan angka contoh atau kuotasi buatan.
