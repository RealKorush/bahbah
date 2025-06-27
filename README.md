# v2ray-probe

اسکریپت Async برای تست دسترس‌پذیری 50K+ لینک V2Ray / VLESS / Trojan / Shadowsocks.

## اجرا در لوکال یا Colab
```bash
pip install -r requirements.txt
python app.py --input configs.txt --output results.csv --concurrency 800
