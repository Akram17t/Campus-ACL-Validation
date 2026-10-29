# Skenario eksperimen

Direktori ini disiapkan untuk skenario dan skrip eksperimen Containerlab.
Belum tersedia skrip eksperimen yang dapat dijalankan.

Rencana alur eksperimen:

1. Siapkan topologi, routing, dan layanan; catat versi image serta konfigurasi.
2. Periksa kesiapan layanan sebelum menerapkan ACL.
3. Kompilasi dan periksa kebijakan, lalu pasang ACL melalui deployer.
4. Jalankan verifier Scapy untuk Staff -> Servers HTTPS, Guest -> Servers DNS
   (UDP/TCP), dan IoT -> Servers MQTT sebagai skenario yang diizinkan.
5. Periksa akses yang ditolak, termasuk Guest -> Servers HTTPS dan port/protokol
   lain yang tidak diizinkan.
6. Catat ekspektasi, hasil aktual, durasi, jumlah paket, serta kesalahan lingkungan
   di `results/`. Bersihkan topologi setelah eksperimen, termasuk saat gagal.

Timeout saja tidak membuktikan bahwa ACL memblokir trafik. Bedakan blokir ACL dari
layanan mati atau routing rusak, dan dokumentasikan metode pengukuran agar hasil
dapat direproduksi.
