import os
import json
import ssl
import socket
import datetime
import html
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def get_ssl_context():
    """Returns an SSL context that works reliably across macOS and Linux environments."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()

class ApiHub:
    def __init__(self, droidzero_url: str, gmail_creds_path: Path, gmail_tokens_dir: Path):
        self.droidzero_url = droidzero_url
        self.gmail_creds_path = gmail_creds_path
        self.gmail_tokens_dir = gmail_tokens_dir
        self.ssl_ctx = get_ssl_context()

    def check_website_status(self) -> Dict[str, any]:
        """Checks DroidZero website availability, response time, and SSL validity."""
        result = {
            "url": self.droidzero_url,
            "is_up": False,
            "status_code": None,
            "latency_ms": None,
            "ssl_days_remaining": None,
            "message": ""
        }

        try:
            start_time = datetime.datetime.now()
            req = urllib.request.Request(
                self.droidzero_url,
                headers={"User-Agent": "Mozilla/5.0 (LifeDashboardBot/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as response:
                latency = (datetime.datetime.now() - start_time).total_seconds() * 1000
                result["is_up"] = (response.status == 200)
                result["status_code"] = response.status
                result["latency_ms"] = round(latency, 1)

            # Check SSL expiration
            hostname = self.droidzero_url.replace("https://", "").replace("http://", "").split("/")[0]
            with socket.create_connection((hostname, 443), timeout=3.0) as sock:
                with self.ssl_ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if cert and 'notAfter' in cert:
                        expire_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                        remaining = (expire_date - datetime.datetime.utcnow()).days
                        result["ssl_days_remaining"] = remaining

            ssl_info = f", SSL: {result['ssl_days_remaining']}d left" if result['ssl_days_remaining'] is not None else ""
            result["message"] = f"🟢 Online (HTTP {result['status_code']}, {result['latency_ms']}ms{ssl_info})"

        except Exception as e:
            result["is_up"] = False
            result["message"] = f"🔴 Offline / Error: {str(e)[:50]}"

        return result

    def get_instance_health(self) -> Dict[str, any]:
        """Collects instance metrics (CPU load, memory, disk)."""
        metrics = {
            "load_avg": "N/A",
            "disk_free_gb": "N/A",
            "services": ["Nginx", "Flask API", "CouchDB", "AdGuard", "Uptime Kuma"]
        }
        try:
            load = os.getloadavg()
            metrics["load_avg"] = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
        except Exception:
            pass

        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            metrics["disk_free_gb"] = f"{free_gb:.1f} GB"
        except Exception:
            pass

        return metrics

    def get_chicago_weather(self) -> Dict[str, any]:
        """
        Fetches real-time weather and hourly precipitation forecast for Chicago using Open-Meteo.
        Tracks if rain/snow is expected and at what time.
        """
        weather = {
            "city": "Chicago, IL",
            "temp_f": None,
            "condition": "N/A",
            "high_f": None,
            "low_f": None,
            "precip_summary": "Dry conditions",
            "summary": "Weather unavailable"
        }
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast?"
                "latitude=41.8781&longitude=-87.6298&"
                "current=temperature_2m,precipitation,weather_code&"
                "hourly=temperature_2m,precipitation_probability,precipitation,rain,snowfall,weather_code&"
                "daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max&"
                "temperature_unit=fahrenheit&precipitation_unit=inch&timezone=America%2FChicago"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "DailyAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as response:
                data = json.loads(response.read().decode())
                current = data.get("current", {})
                daily = data.get("daily", {})
                hourly = data.get("hourly", {})

                temp = round(current.get("temperature_2m", 0), 1)
                high = round(daily.get("temperature_2m_max", [0])[0], 1)
                low = round(daily.get("temperature_2m_min", [0])[0], 1)
                max_prob = daily.get("precipitation_probability_max", [0])[0]
                precip_sum = daily.get("precipitation_sum", [0])[0]

                # Analyze hourly precipitation forecast starting from current hour
                now = datetime.datetime.now()
                current_hour_iso = now.strftime("%Y-%m-%dT%H:00")
                times = hourly.get("time", [])
                start_idx = 0
                for idx, t_str in enumerate(times):
                    if t_str >= current_hour_iso:
                        start_idx = idx
                        break

                rain_start_time = None
                rain_prob = 0
                rain_amount = 0.0
                is_snow = False

                # Scan next 18 hours for upcoming precipitation
                for i in range(start_idx, min(start_idx + 18, len(times))):
                    h_time = times[i]
                    h_prob = hourly.get("precipitation_probability", [])[i] if i < len(hourly.get("precipitation_probability", [])) else 0
                    h_precip = hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else 0
                    h_snow = hourly.get("snowfall", [])[i] if i < len(hourly.get("snowfall", [])) else 0

                    if h_snow > 0.01:
                        is_snow = True
                        h_dt = datetime.datetime.fromisoformat(h_time)
                        rain_start_time = h_dt.strftime("%I:%M %p").lstrip("0")
                        rain_prob = h_prob
                        rain_amount = h_snow
                        break

                    if (h_prob >= 30 and h_precip >= 0.01) or h_precip >= 0.02:
                        h_dt = datetime.datetime.fromisoformat(h_time)
                        rain_start_time = h_dt.strftime("%I:%M %p").lstrip("0")
                        rain_prob = h_prob
                        rain_amount = h_precip
                        break

                if is_snow:
                    precip_note = f"❄️ Snow expected starting around {rain_start_time} ({rain_prob}% chance)"
                elif rain_start_time:
                    precip_note = f"🌧️ Rain expected starting ~{rain_start_time} ({rain_prob}% chance, ~{rain_amount:.2f}\")"
                elif max_prob and max_prob >= 25:
                    precip_note = f"⛅ Slight chance of showers ({max_prob}%), mostly dry"
                else:
                    precip_note = "☀️ No rain or snow expected today (0% precip)"

                weather["temp_f"] = temp
                weather["high_f"] = high
                weather["low_f"] = low
                weather["precip_summary"] = precip_note
                weather["summary"] = f"{temp}°F (High: {high}°F / Low: {low}°F) • {precip_note}"
        except Exception as e:
            weather["summary"] = f"Chicago Weather: Unavailable ({str(e)[:25]})"

        return weather

    def get_daily_news(self) -> Dict[str, any]:
        """
        Fetches today's top news headlines from reliable RSS feeds:
        - Chicago: WGN-TV Chicago (primary), NBC 5 Chicago (fallback)
        - US: NPR News (primary), ABC News (fallback)
        - World: BBC World News (primary), Al Jazeera English (fallback)
        Returns structured dictionary with titles, sources, and links.
        """
        feeds = {
            "chicago": [
                ("https://wgntv.com/news/chicago-news/feed/", "WGN-TV Chicago"),
                ("https://www.nbcchicago.com/?rss=y", "NBC 5 Chicago"),
            ],
            "us": [
                ("https://feeds.npr.org/1001/rss.xml", "NPR News"),
                ("https://abcnews.go.com/abcnews/usheadlines", "ABC News"),
            ],
            "world": [
                ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World News"),
                ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera English"),
            ]
        }

        req_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        news_results = {}

        for category, sources in feeds.items():
            item_found = False
            for url, source_name in sources:
                try:
                    req = urllib.request.Request(url, headers=req_headers)
                    with urllib.request.urlopen(req, timeout=7, context=self.ssl_ctx) as resp:
                        content = resp.read()
                        root = ET.fromstring(content)
                        items = root.findall("./channel/item")
                        if not items:
                            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
                        if items:
                            top_item = items[0]
                            title_elem = top_item.find("title")
                            if title_elem is None:
                                title_elem = top_item.find("{http://www.w3.org/2005/Atom}title")
                            title_text = title_elem.text if title_elem is not None and title_elem.text else "Top stories"

                            clean_title = html.unescape(title_text).strip()
                            clean_title = clean_title.replace("<![CDATA[", "").replace("]]>", "").strip()
                            for suffix in [f" - {source_name}", f" | {source_name}"]:
                                if clean_title.endswith(suffix):
                                    clean_title = clean_title[:-len(suffix)].strip()

                            link_elem = top_item.find("link")
                            if link_elem is None:
                                link_elem = top_item.find("{http://www.w3.org/2005/Atom}link")
                            link_url = ""
                            if link_elem is not None:
                                link_url = link_elem.text or link_elem.attrib.get("href", "")
                            link_url = link_url.strip()

                            news_results[category] = {
                                "title": clean_title,
                                "source": source_name,
                                "link": link_url,
                                "status": "OK"
                            }
                            item_found = True
                            break
                except Exception:
                    continue

            if not item_found:
                news_results[category] = {
                    "title": f"Top {category.capitalize()} news headlines",
                    "source": "News Feed",
                    "link": "",
                    "status": "Unavailable"
                }

        return news_results

    def get_market_watchlist(self, tickers: List[str], target_date: Optional[datetime.date] = None) -> List[Dict[str, any]]:
        """
        Fetches market quotes with 🟢 Green / 🔴 Red indicator.
        Only runs on weekdays (Monday - Friday). On weekends, returns market closed indicator.
        """
        current_date = target_date or datetime.date.today()
        # Saturday = 5, Sunday = 6
        if current_date.weekday() >= 5:
            return [{
                "symbol": "CLOSED",
                "price": "-",
                "change_pct": "-",
                "indicator": "",
                "display": "*Markets closed on weekends.*",
                "is_weekend": True
            }]

        quotes = []
        for ticker in tickers:
            clean_ticker = ticker.strip().upper()
            item = {
                "symbol": clean_ticker,
                "price": "N/A",
                "change_pct": "0.0%",
                "indicator": "⚪",
                "display": f"**{clean_ticker}**: N/A",
                "is_weekend": False
            }
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_ticker}?interval=1d&range=1d"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
                )
                with urllib.request.urlopen(req, timeout=4, context=self.ssl_ctx) as resp:
                    data = json.loads(resp.read().decode())
                    result = data.get("chart", {}).get("result")
                    if result:
                        meta = result[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
                        if price is not None and prev_close:
                            change = ((price - prev_close) / prev_close) * 100
                            indicator = "🟢" if change > 0 else ("🔴" if change < 0 else "⚪")
                            item["price"] = f"${price:,.2f}"
                            item["indicator"] = indicator
                            item["change_pct"] = f"{indicator} {'+' if change >= 0 else ''}{change:.2f}%"
                            item["display"] = f"**{clean_ticker}**: {item['price']} ({item['change_pct']})"
            except Exception:
                item["display"] = f"**{clean_ticker}**: Tracked"

            quotes.append(item)
        return quotes

    def _get_access_token(self, token_file: Path) -> tuple:
        """Refreshes and returns a valid access token from a token JSON file."""
        if not token_file.exists():
            return None, "Token file not found"
        try:
            import urllib.parse
            data = json.loads(token_file.read_text(encoding="utf-8"))
            refresh_token = data.get("refresh_token")
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")

            if not refresh_token or not client_id:
                return None, "Missing refresh token"

            token_url = data.get("token_uri", "https://oauth2.googleapis.com/token")
            post_data = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }).encode("utf-8")

            req = urllib.request.Request(
                token_url,
                data=post_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            with urllib.request.urlopen(req, timeout=8, context=self.ssl_ctx) as resp:
                res = json.loads(resp.read().decode())
                access_token = res.get("access_token")

            if not access_token:
                return None, "No access token received"

            return access_token, None
        except urllib.error.HTTPError as he:
            if he.code == 400:
                return None, "Token expired (invalid_grant)"
            return None, f"HTTP {he.code}"
        except Exception as e:
            return None, str(e)[:35]

    def get_gmail_triage(self, max_candidates: int = 5) -> Dict[str, any]:
        """
        Reads Gmail unread counts and surfaces priority unread emails using native HTTP REST requests.
        Scores candidate emails (prioritizing packages, bills, security alerts, and human messages over promo/newsletters).
        """
        triage = {
            "account_a_unread": 0,
            "account_b_unread": 0,
            "status": "Ready",
            "action_required": "",
            "candidates": [],
            "top_email": None
        }

        token_1 = self.gmail_tokens_dir / "token_1.json"
        token_2 = self.gmail_tokens_dir / "token_2.json"

        if not token_1.exists() and not token_2.exists():
            triage["status"] = "⚠️ Gmail Offline (Tokens not found in credentials dir)"
            triage["action_required"] = "Run python3 reauth_google.py to authenticate"
            return triage

        all_candidates = []

        def query_account(account_label: str, token_file: Path) -> tuple:
            access_token, err = self._get_access_token(token_file)
            if err:
                return 0, [], err

            try:
                api_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread+label:INBOX&maxResults=50"
                api_req = urllib.request.Request(
                    api_url,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                with urllib.request.urlopen(api_req, timeout=6, context=self.ssl_ctx) as api_resp:
                    api_data = json.loads(api_resp.read().decode())
                    messages = api_data.get("messages", [])
                    total_count = len(messages)

                account_candidates = []
                for m in messages[:max_candidates]:
                    m_id = m.get("id")
                    if not m_id:
                        continue
                    m_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m_id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date"
                    m_req = urllib.request.Request(
                        m_url,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    try:
                        with urllib.request.urlopen(m_req, timeout=5, context=self.ssl_ctx) as m_resp:
                            m_obj = json.loads(m_resp.read().decode())
                            headers = {h.get("name", ""): h.get("value", "") for h in m_obj.get("payload", {}).get("headers", [])}
                            subj = html.unescape(headers.get("Subject", "No Subject")).strip()
                            sender = html.unescape(headers.get("From", "Unknown Sender")).strip()
                            date_str = headers.get("Date", "").strip()
                            snippet = html.unescape(m_obj.get("snippet", "")).strip()
                            label_ids = m_obj.get("labelIds", [])

                            score = 0
                            if "IMPORTANT" in label_ids:
                                score += 15

                            combined = f"{subj.lower()} {sender.lower()} {snippet.lower()}"
                            priority_keywords = [
                                "package", "delivery", "delivered", "locker", "access code", "tracking",
                                "payment", "due", "bill", "invoice", "statement", "receipt",
                                "flight", "ticket", "boarding", "reservation", "booking", "itinerary",
                                "security alert", "verification code", "two-factor", "password reset",
                                "urgent", "action required", "reminder", "appointment", "doctor", "health"
                            ]
                            for kw in priority_keywords:
                                if kw in combined:
                                    score += 10
                                    break

                            marketing_keywords = [
                                "unsubscribe", "newsletter", "weekly digest", "daily digest",
                                "promo", "sale", "discount", "special offer", "save %", "off your next",
                                "webinar", "podcast", "medium digest", "substack", "linkedin job",
                                "marketing", "no-reply", "noreply"
                            ]
                            for kw in marketing_keywords:
                                if kw in combined:
                                    score -= 8

                            account_candidates.append({
                                "account": account_label,
                                "id": m_id,
                                "subject": subj,
                                "sender": sender,
                                "date": date_str,
                                "snippet": snippet,
                                "is_important": "IMPORTANT" in label_ids,
                                "score": score
                            })
                    except Exception:
                        continue

                return total_count, account_candidates, None
            except urllib.error.HTTPError as he:
                if he.code in (401, 403):
                    return 0, [], "Insufficient permissions or expired token"
                return 0, [], f"HTTP {he.code}"
            except Exception as e:
                return 0, [], str(e)[:30]

        count_1, cands_1, err_1 = query_account("Account A", token_1)
        count_2, cands_2, err_2 = query_account("Account B", token_2)

        if err_1 == "Token expired (invalid_grant)" or err_2 == "Token expired (invalid_grant)":
            triage["status"] = "⚠️ Action Required: Re-auth needed (`python3 reauth_google.py`)"
            triage["action_required"] = "Run python3 reauth_google.py once to re-authorize Google OAuth"
        elif err_1 or err_2:
            triage["status"] = f"⚠️ Gmail Sync: {err_1 or err_2}"
        else:
            triage["account_a_unread"] = count_1
            triage["account_b_unread"] = count_2
            triage["status"] = f"🟢 Account A: {count_1} unread • Account B: {count_2} unread"

        all_candidates.extend(cands_1)
        all_candidates.extend(cands_2)

        all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        triage["candidates"] = all_candidates

        if all_candidates:
            top = all_candidates[0]
            summary = top["snippet"]
            if len(summary) > 220:
                summary = summary[:217] + "..."
            triage["top_email"] = {
                "account": top["account"],
                "sender": top["sender"],
                "subject": top["subject"],
                "snippet": top["snippet"],
                "summary": summary
            }

        return triage

    def _parse_ics_feed(
        self,
        ics_text: str,
        target_date: datetime.date,
        default_tz: any
    ) -> Tuple[List[Dict[str, any]], str]:
        """
        Parses an iCalendar (.ics) feed (e.g. iCloud, Apple Calendar, Outlook) according to RFC 5545.
        Handles line unfolding, DTSTART/DTEND (timed vs all-day), timezones, and basic RRULE recurrence.
        """
        events: List[Dict[str, any]] = []
        if not ics_text:
            return events, "iCloud"

        # 1. RFC 5545 Line Unfolding: Remove CRLF followed by space or tab
        unfolded = re.sub(r'\r?\n[ \t]', '', ics_text)

        # 2. Extract Calendar Name
        cal_name_match = re.search(r'^X-WR-CALNAME:(.+)$', unfolded, re.MULTILINE)
        cal_name = cal_name_match.group(1).strip() if cal_name_match else "iCloud"

        # Fallback timezone if default_tz is None
        if not default_tz:
            try:
                from zoneinfo import ZoneInfo
                default_tz = ZoneInfo("America/Chicago")
            except Exception:
                default_tz = datetime.timezone(datetime.timedelta(hours=-5))

        def parse_ics_dt(dt_line: str) -> Tuple[Optional[datetime.datetime], bool]:
            parts = dt_line.split(":", 1)
            if len(parts) != 2:
                return None, False
            params_part, val = parts[0], parts[1].strip()
            is_date_only = "VALUE=DATE" in params_part or len(val) == 8

            if is_date_only:
                try:
                    d = datetime.date(int(val[:4]), int(val[4:6]), int(val[6:8]))
                    dt = datetime.datetime.combine(d, datetime.time.min).replace(tzinfo=default_tz)
                    return dt, True
                except Exception:
                    return None, True

            # Timed event
            tz = default_tz
            if "TZID=" in params_part:
                tz_str = params_part.split("TZID=")[1].split(";")[0].strip()
                try:
                    from zoneinfo import ZoneInfo
                    tz = ZoneInfo(tz_str)
                except Exception:
                    if "GMT" in tz_str:
                        m = re.match(r'GMT([+-]\d{2})(\d{2})?', tz_str)
                        if m:
                            hours = int(m.group(1))
                            mins = int(m.group(2) or 0)
                            tz = datetime.timezone(datetime.timedelta(hours=hours, minutes=mins))

            if val.endswith("Z"):
                try:
                    val_clean = val[:-1]
                    dt_utc = datetime.datetime.strptime(val_clean, "%Y%m%dT%H%M%S").replace(tzinfo=datetime.timezone.utc)
                    return dt_utc.astimezone(default_tz), False
                except Exception:
                    return None, False
            else:
                try:
                    naive = datetime.datetime.strptime(val, "%Y%m%dT%H%M%S")
                    return naive.replace(tzinfo=tz).astimezone(default_tz), False
                except Exception:
                    return None, False

        vevents = unfolded.split("BEGIN:VEVENT")
        for block in vevents[1:]:
            if "END:VEVENT" not in block:
                continue
            body = block.split("END:VEVENT")[0]

            summary = "iCloud Event"
            location = ""
            status = ""
            dtstart_line = ""
            dtend_line = ""
            rrule_line = ""
            url_line = ""

            for line in body.splitlines():
                line = line.strip()
                if line.startswith("SUMMARY"):
                    summary = line.split(":", 1)[-1].replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\").strip()
                elif line.startswith("LOCATION"):
                    location = line.split(":", 1)[-1].replace(r"\,", ",").replace(r"\n", " ").replace(r"\\", "\\").strip()
                elif line.startswith("STATUS"):
                    status = line.split(":", 1)[-1].strip().upper()
                elif line.startswith("DTSTART"):
                    dtstart_line = line
                elif line.startswith("DTEND"):
                    dtend_line = line
                elif line.startswith("RRULE:"):
                    rrule_line = line[6:].strip()
                elif line.startswith("URL"):
                    url_line = line.split(":", 1)[-1].strip()

            if status == "CANCELLED":
                continue

            start_dt, is_all_day = parse_ics_dt(dtstart_line) if dtstart_line else (None, False)
            if not start_dt:
                continue

            end_dt = None
            if dtend_line:
                end_dt, _ = parse_ics_dt(dtend_line)

            matches = False
            if is_all_day:
                s_date = start_dt.date()
                e_date = end_dt.date() if end_dt else s_date + datetime.timedelta(days=1)
                if s_date <= target_date < e_date:
                    matches = True
            else:
                if start_dt.date() == target_date:
                    matches = True

            # Handle recurrence (RRULE) if not matched directly
            if not matches and rrule_line:
                r_parts = dict(part.split("=", 1) for part in rrule_line.split(";") if "=" in part)
                freq = r_parts.get("FREQ")
                until_str = r_parts.get("UNTIL")
                until_dt = None
                if until_str:
                    until_dt, _ = parse_ics_dt("DT:" + until_str)

                if not until_dt or target_date <= until_dt.date():
                    if freq == "YEARLY":
                        if start_dt.month == target_date.month and start_dt.day == target_date.day:
                            matches = True
                    elif freq == "DAILY":
                        interval = int(r_parts.get("INTERVAL", 1))
                        diff_days = (target_date - start_dt.date()).days
                        if diff_days >= 0 and diff_days % interval == 0:
                            matches = True
                    elif freq == "WEEKLY":
                        byday = r_parts.get("BYDAY", "")
                        interval = int(r_parts.get("INTERVAL", 1))
                        diff_weeks = (target_date - start_dt.date()).days // 7
                        day_abbr = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][target_date.weekday()]
                        if diff_weeks >= 0 and (diff_weeks % interval == 0):
                            if not byday or day_abbr in byday.split(","):
                                matches = True

            if matches:
                if is_all_day:
                    time_display = "All Day"
                    sort_key = 0
                else:
                    start_fmt = start_dt.strftime("%I:%M %p").lstrip("0")
                    if end_dt:
                        end_fmt = end_dt.strftime("%I:%M %p").lstrip("0")
                        time_display = f"{start_fmt} – {end_fmt}"
                    else:
                        time_display = start_fmt
                    sort_key = start_dt.timestamp()

                # Extract meeting URL if present
                meet_link = ""
                for candidate in [url_line, location]:
                    m = re.search(r'(https?://[^\s]+)', candidate)
                    if m:
                        candidate_url = m.group(1)
                        if any(domain in candidate_url.lower() for domain in ["meet.google", "zoom.us", "teams.microsoft", "webex", "facetime.apple"]):
                            meet_link = candidate_url
                            break

                events.append({
                    "summary": summary,
                    "time_display": time_display,
                    "is_all_day": is_all_day,
                    "sort_key": sort_key,
                    "account": "iCloud",
                    "calendar": cal_name,
                    "meet_link": meet_link,
                    "location": location
                })

        return events, cal_name

    def get_calendar_events(
        self,
        target_date: datetime.date,
        timezone_name: str = "America/Chicago",
        ics_urls: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Fetches scheduled events for target_date across all connected Google accounts and calendars.
        Also parses optional external iCal (.ics) URLs if provided.
        Returns chronologically sorted events ready for inclusion in the Daily Note To-do section.
        """
        import urllib.parse

        result = {
            "events": [],
            "calendar_lines": [],
            "count": 0,
            "status": "Ready",
            "accounts_polled": []
        }

        # Resolve local timezone
        tz = None
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone_name)
        except Exception:
            pass

        # Construct ISO start and end timestamps for the target day
        target_str = target_date.strftime("%Y-%m-%d")
        if tz:
            start_dt = datetime.datetime.combine(target_date, datetime.time.min).replace(tzinfo=tz)
            end_dt = datetime.datetime.combine(target_date, datetime.time.max).replace(tzinfo=tz)
            time_min = start_dt.isoformat()
            time_max = end_dt.isoformat()
        else:
            # Fallback assuming Chicago (CDT UTC-5 / CST UTC-6)
            time_min = f"{target_str}T00:00:00-05:00"
            time_max = f"{target_str}T23:59:59-05:00"

        accounts = [
            ("Account A", self.gmail_tokens_dir / "token_1.json"),
            ("Account B", self.gmail_tokens_dir / "token_2.json"),
        ]

        all_events = []
        scope_warning = False

        for account_label, token_file in accounts:
            if not token_file.exists():
                continue

            result["accounts_polled"].append(account_label)
            access_token, err = self._get_access_token(token_file)
            if err:
                continue

            # 1. Fetch user's calendar list
            cal_list_url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
            cal_req = urllib.request.Request(
                cal_list_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            calendars_to_query = []
            try:
                with urllib.request.urlopen(cal_req, timeout=6, context=self.ssl_ctx) as cal_resp:
                    cal_data = json.loads(cal_resp.read().decode())
                    items = cal_data.get("items", [])
                    for c in items:
                        # Include primary or selected non-hidden calendars
                        if c.get("selected", False) or c.get("primary", False):
                            if not c.get("hidden", False):
                                calendars_to_query.append((c["id"], c.get("summary", "Calendar")))
            except urllib.error.HTTPError as he:
                if he.code in (401, 403):
                    scope_warning = True
                continue
            except Exception:
                continue

            # Fallback to 'primary' if list is empty but token is valid
            if not calendars_to_query and not scope_warning:
                calendars_to_query.append(("primary", "Primary"))

            # 2. Query events for each calendar
            for cal_id, cal_name in calendars_to_query:
                try:
                    enc_id = urllib.parse.quote(cal_id)
                    enc_min = urllib.parse.quote(time_min)
                    enc_max = urllib.parse.quote(time_max)
                    events_url = (
                        f"https://www.googleapis.com/calendar/v3/calendars/{enc_id}/events?"
                        f"timeMin={enc_min}&timeMax={enc_max}&singleEvents=true&orderBy=startTime"
                    )
                    ev_req = urllib.request.Request(
                        events_url,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    with urllib.request.urlopen(ev_req, timeout=6, context=self.ssl_ctx) as ev_resp:
                        ev_data = json.loads(ev_resp.read().decode())
                        for item in ev_data.get("items", []):
                            if item.get("status") == "cancelled":
                                continue

                            summary = item.get("summary", "(No title)").strip()
                            start_info = item.get("start", {})
                            end_info = item.get("end", {})

                            is_all_day = "date" in start_info
                            sort_key = 0

                            if is_all_day:
                                time_display = "All Day"
                                sort_key = 0
                            else:
                                start_dt_str = start_info.get("dateTime", "")
                                end_dt_str = end_info.get("dateTime", "")
                                try:
                                    s_dt = datetime.datetime.fromisoformat(start_dt_str)
                                    if tz and s_dt.tzinfo:
                                        s_dt = s_dt.astimezone(tz)
                                    sort_key = s_dt.timestamp()
                                    start_time_fmt = s_dt.strftime("%I:%M %p").lstrip("0")

                                    if end_dt_str:
                                        e_dt = datetime.datetime.fromisoformat(end_dt_str)
                                        if tz and e_dt.tzinfo:
                                            e_dt = e_dt.astimezone(tz)
                                        end_time_fmt = e_dt.strftime("%I:%M %p").lstrip("0")
                                        time_display = f"{start_time_fmt} – {end_time_fmt}"
                                    else:
                                        time_display = start_time_fmt
                                except Exception:
                                    time_display = "Scheduled"
                                    sort_key = 1

                            meet_link = item.get("hangoutLink", "")
                            location = item.get("location", "")

                            all_events.append({
                                "summary": summary,
                                "time_display": time_display,
                                "is_all_day": is_all_day,
                                "sort_key": sort_key,
                                "account": account_label,
                                "calendar": cal_name,
                                "meet_link": meet_link,
                                "location": location
                            })
                except urllib.error.HTTPError as he:
                    if he.code in (401, 403):
                        scope_warning = True
                    continue
                except Exception:
                    continue

        # 3. External iCal (.ics / webcal) feeds (e.g. iCloud Calendar)
        if ics_urls:
            for ics_url in ics_urls:
                if not ics_url:
                    continue
                if ics_url.startswith("webcal://"):
                    ics_url = "https://" + ics_url[9:]
                if not ics_url.startswith("http://") and not ics_url.startswith("https://"):
                    continue
                try:
                    ics_req = urllib.request.Request(ics_url, headers={"User-Agent": "DailyAssistant/1.0"})
                    with urllib.request.urlopen(ics_req, timeout=8, context=self.ssl_ctx) as ics_resp:
                        ics_text = ics_resp.read().decode("utf-8", errors="ignore")
                        ics_events, cal_title = self._parse_ics_feed(ics_text, target_date, tz)
                        all_events.extend(ics_events)
                        if "iCloud" not in result["accounts_polled"]:
                            result["accounts_polled"].append("iCloud")
                except Exception:
                    pass

        # Deduplicate identical events (same summary and time)
        deduped = []
        seen = set()
        for ev in all_events:
            k = (ev["summary"].lower(), ev["time_display"])
            if k not in seen:
                seen.add(k)
                deduped.append(ev)

        # Sort: all-day events first, then chronological by sort_key
        deduped.sort(key=lambda x: (not x["is_all_day"], x["sort_key"]))

        # Build markdown lines for To-do section
        calendar_lines = []
        for ev in deduped:
            meet_part = f" ([Join Meet]({ev['meet_link']}))" if ev["meet_link"] else ""
            acc_tag = f" *({ev['account']})*" if (len(result["accounts_polled"]) > 1 or ev["account"] == "iCloud") else ""

            if ev["is_all_day"]:
                line = f"- [ ] 🗓️ **All Day**: {ev['summary']}{acc_tag}"
            else:
                line = f"- [ ] ⏰ **{ev['time_display']}**: {ev['summary']}{meet_part}{acc_tag}"
            calendar_lines.append(line)

        result["events"] = deduped
        result["calendar_lines"] = calendar_lines
        result["count"] = len(deduped)

        if scope_warning:
            result["status"] = "⚠️ Google Calendar scope not authorized (run `python3 reauth_google.py`)"
        elif deduped:
            result["status"] = f"🟢 {len(deduped)} event{'s' if len(deduped) != 1 else ''} scheduled today"
        else:
            result["status"] = "🟢 0 events scheduled today"

        return result

    @staticmethod
    def extract_system_incidents(api_data: Dict[str, any]) -> List[str]:
        """
        Scans polled system metrics for outages, degraded performance, unauthorized scopes,
        or impending failures. Returns a list of actionable issue summaries that must be
        investigated as To-dos.
        """
        incidents = []

        # 1. Website Status (DroidZero)
        website = api_data.get("website", {})
        web_status = str(website.get("status", "")).lower()
        if web_status in ("offline", "degraded", "error"):
            msg = website.get("message", "Website unreachable")
            incidents.append(f"Investigate DroidZero website downtime ({msg})")
        else:
            ssl_days = website.get("ssl_days_left")
            if ssl_days is not None:
                try:
                    if int(ssl_days) < 14:
                        incidents.append(f"Renew DroidZero SSL certificate: expires in {ssl_days} days")
                except (ValueError, TypeError):
                    pass

        # 2. Server Instance Health (OCI VM)
        instance = api_data.get("instance", {})
        disk_free = instance.get("disk_free_gb")
        if disk_free is not None:
            try:
                if float(disk_free) < 10.0:
                    incidents.append(f"Free up OCI server disk space: only {disk_free} GB remaining")
            except (ValueError, TypeError):
                pass
        inst_status = str(instance.get("status", "")).lower()
        if "high load" in inst_status:
            incidents.append(f"Investigate OCI server high CPU load: {instance.get('load_avg', 'N/A')}")

        # 3. Google Calendar Sync
        cal = api_data.get("calendar", {})
        cal_status = str(cal.get("status", "")).lower()
        if "reauth" in cal_status or "scope not authorized" in cal_status:
            incidents.append("Reauthorize Google Calendar API: Run `python3 reauth_google.py` in terminal to restore calendar sync")
        elif "error" in cal_status or "failed" in cal_status:
            incidents.append(f"Investigate Google Calendar sync failure: {cal.get('status')}")

        # 4. Gmail Inboxes Triage
        gmail = api_data.get("gmail", {})
        gmail_status = str(gmail.get("status", "")).lower()
        if "error" in gmail_status or "failed" in gmail_status or ("action" in gmail_status and "auth" in gmail_status):
            incidents.append(f"Investigate Gmail API failure: {gmail.get('status')}")

        # 5. Weather Feed
        weather = api_data.get("weather", {})
        if weather.get("status") == "Unavailable" or "error" in str(weather.get("summary", "")).lower():
            incidents.append("Investigate Chicago weather API failure (Open-Meteo endpoint unreachable)")

        return incidents

