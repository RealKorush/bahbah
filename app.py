#!/usr/bin/env python3
"""
اسکریپت تست سلامتی لینک‌های VMESS / VLESS / Trojan / Shadowsocks و …
نویسنده: شما :)
"""
import asyncio, argparse, base64, csv, re, ssl, time
from urllib.parse import urlparse

# ------- RegEx-ها و توابع کمکی --------
URI_SCHEME = re.compile(r'^(?P<scheme>[a-z0-9+.-]+)://(?P<rest>.+)$', re.I)

def parse_link(link: str):
    """
    ورودی: یک URI کانفیگ
    خروجی: (host:str|None, port:int|None)
    """
    link = link.strip()
    m = URI_SCHEME.match(link)
    if not m:
        return None, None
    scheme, rest = m.group('scheme').lower(), m.group('rest')

    try:
        # Shadowsocks ممکن است base64 باشد
        if scheme == 'ss' and rest.startswith('//'):
            rest = rest[2:]
            if ':' not in rest:
                # ss://BASE64
                decoded = base64.urlsafe_b64decode(rest.split('#')[0] + '===').decode()
                rest    = decoded.split('@')[-1]          # <host>:<port>
            else:
                rest = rest.split('@')[-1]                # cipher:pass@host:port → host:port
        else:
            # vless://uuid@host:port?... یا trojan://pass@host:port
            rest = rest.split('@')[-1]                    # …@host:port
        host, port = rest.split(':', 1)
        return host.strip('[]'), int(port.split('/')[0])
    except Exception:
        return None, None

async def probe(host: str, port: int, timeout: float = 3.0):
    """
    اتصال TCP ساده برای سنجش دسترس‌پذیری؛ در صورت موفق، زمان اتصال (میلی‌ثانیه) را برمی‌گرداند.
    """
    t0 = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=None), timeout
        )
        writer.close()
        await writer.wait_closed()
        return round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        return None

async def worker(sem, link, rows, timeout):
    host, port = parse_link(link)
    if host is None:
        rows.append((link, '', '', 'invalid', ''))
        return
    async with sem:
        latency = await probe(host, port, timeout)
    rows.append((link, host, port, 'alive' if latency else 'dead', latency or ''))

async def main(cfg):
    with open(cfg.input, encoding='utf-8') as f:
        links = [l for l in map(str.strip, f) if l]

    sem   = asyncio.Semaphore(cfg.concurrency)
    rows  = []
    tasks = [worker(sem, link, rows, cfg.timeout) for link in links]

    # gather را به صورت تکه‌تکه اجرا می‌کنیم تا رم نترکد
    for i in range(0, len(tasks), cfg.concurrency):
        await asyncio.gather(*tasks[i:i + cfg.concurrency])

    with open(cfg.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['link', 'host', 'port', 'status', 'latency_ms'])
        w.writerows(rows)
    print(f"✓ ذخیره شد → {cfg.output}")

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='V2Ray links health checker')
    p.add_argument('--input',  default='configs.txt', help='فایل ورودی')
    p.add_argument('--output', default='results.csv', help='فایل خروجی CSV')
    p.add_argument('--concurrency', type=int, default=1000, help='تعداد کانکشن هم‌زمان')
    p.add_argument('--timeout',     type=float, default=3.0, help='ثانیه تایم‌اوت TCP')
    cfg = p.parse_args()
    asyncio.run(main(cfg))
