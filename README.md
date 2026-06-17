# آگاه کراودفاند — راهنمای راه‌اندازی

## ساختار فایل‌ها

```
agahcrowdfund/
├── index.html              # داشبورد اصلی (بدون سرور کار می‌کند)
├── scraper.py              # اسکرپر هوشمند (فقط پروژه‌های جدید)
├── data.json               # داده‌ها (به‌طور خودکار آپدیت می‌شود)
├── requirements.txt        # کتابخانه‌های پایتون
└── .github/
    └── workflows/
        └── scrape.yml      # زمان‌بندی خودکار هر ۲۴ ساعت
```

---

## مرحله ۱ — اجرای اول روی کامپیوتر شخصی

این مرحله را **فقط یک بار** اجرا کنید تا داده‌های کامل جمع‌آوری شود.

### پیش‌نیازها

- Python 3 نصب باشد
- اینترنت داشته باشید

### دستورات

```bash
# نصب کتابخانه‌ها (یک بار)
pip install -r requirements.txt

# اجرای اسکرپر (45-60 دقیقه طول می‌کشد)
python scraper.py
```

بعد از اتمام، فایل `data.json` ساخته می‌شود.

---

## مرحله ۲ — ساخت مخزن GitHub

1. به [github.com](https://github.com) بروید و وارد شوید
2. روی **New repository** کلیک کنید
3. نام را بگذارید: `agahcrowdfund`
4. تیک **Public** بزنید
5. روی **Create repository** کلیک کنید

### آپلود فایل‌ها

```bash
# در پوشه پروژه
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/agahcrowdfund.git
git push -u origin main
```

`YOUR_USERNAME` را با نام کاربری GitHub خود عوض کنید.

---

## مرحله ۳ — راه‌اندازی GitHub Actions

این مرحله به‌طور خودکار انجام می‌شود — فایل `.github/workflows/scrape.yml` این کار را می‌کند.

برای اجرای دستی:
1. در GitHub به تب **Actions** بروید
2. روی **Scrape IFB Projects** کلیک کنید
3. روی **Run workflow** کلیک کنید

---

## مرحله ۴ — راه‌اندازی Cloudflare Pages

1. به [dash.cloudflare.com](https://dash.cloudflare.com) بروید
2. روی **Pages** کلیک کنید
3. روی **Create a project** → **Connect to Git** کلیک کنید
4. مخزن `agahcrowdfund` را انتخاب کنید
5. تنظیمات Build:
   - **Framework preset**: None
   - **Build command**: خالی بگذارید
   - **Build output directory**: `/` (یا خالی)
6. روی **Save and Deploy** کلیک کنید

---

## مرحله ۵ — اتصال دامنه agahcrowdfund.ir

### در Cloudflare Pages:
1. به پروژه Pages بروید
2. روی **Custom domains** کلیک کنید
3. **Add a custom domain** را بزنید
4. تایپ کنید: `agahcrowdfund.ir`
5. دستورالعمل DNS را دنبال کنید

### در تنظیمات DNS Cloudflare:
یک رکورد CNAME بسازید:
- **Type**: CNAME
- **Name**: `agahcrowdfund.ir` یا `@`
- **Target**: آدرسی که Cloudflare Pages به شما می‌دهد
- **Proxy**: روشن (نارنجی)

---

## نحوه کارکرد

```
هر ۲۴ ساعت:
GitHub Actions → scraper.py اجرا می‌شود
               → فقط صفحه‌های اول ifb.ir بررسی می‌شود
               → اگر پروژه جدید بود، اضافه می‌شود
               → data.json آپدیت می‌شود
               → Cloudflare خودکار آپدیت می‌کند

کاربر:
agahcrowdfund.ir → Cloudflare Pages → index.html
index.html → data.json را می‌خواند → داشبورد نمایش می‌دهد
```

---

## هزینه

| سرویس | هزینه |
|---|---|
| GitHub | رایگان |
| GitHub Actions | رایگان (تا ۲۰۰۰ دقیقه/ماه) |
| Cloudflare Pages | رایگان |
| دامنه agahcrowdfund.ir | پرداخت شده (دارید) |

**جمع: صفر تومان هزینه ماهانه**
