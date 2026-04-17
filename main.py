import datetime
import os
import json
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

# 1. AUTHENTICATE WITH SECRETS
app_id = os.environ.get('META_APP_ID')
app_secret = os.environ.get('META_APP_SECRET')
access_token = os.environ.get('META_ACCESS_TOKEN')
ad_account_id = os.environ.get('META_AD_ACCOUNT_ID')

FacebookAdsApi.init(app_id, app_secret, access_token)
account = AdAccount(ad_account_id)

# 2. DEFINE THE PRESETS (LOCKED TO IST)
utc_now = datetime.datetime.utcnow()
ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
today = ist_now.date()
yesterday = today - datetime.timedelta(days=1)

presets = {
    'today': (today, today),
    'yesterday': (yesterday, yesterday),
    'last_2_days': (today - datetime.timedelta(days=2), yesterday),
    'last_3_days': (today - datetime.timedelta(days=3), yesterday),
    'last_7_days': (today - datetime.timedelta(days=7), yesterday),
    'last_30_days': (today - datetime.timedelta(days=30), yesterday)
}

def get_status(condition, good_text="Good", bad_text="Action needed", watch=False):
    if condition: return f"<span class='badge badge-good'>{good_text}</span>"
    if watch: return f"<span class='badge badge-watch'>{bad_text}</span>"
    return f"<span class='badge badge-bad'>{bad_text}</span>"

all_data = {}

print("Fetching data for all presets...")

# 3. FETCH AND PROCESS ALL PRESETS
for period, (start_date, end_date) in presets.items():
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    params = {'time_range': {'since': start_str, 'until': end_str}, 'level': 'account'}
    fields = ['spend', 'reach', 'impressions', 'inline_link_clicks', 'actions']
    
    try:
        insights = account.get_insights(fields=fields, params=params)
    except Exception as e:
        print(f"Error fetching {period}: {e}")
        insights = []

    # Parse
    raw = {'spend': 0.0, 'reach': 0, 'impressions': 0, 'link_clicks': 0, 'lpv': 0, 'atc': 0, 'chk': 0, 'pay': 0, 'pur': 0}
    if insights:
        row = insights[0]
        raw['spend'] = float(row.get('spend', 0))
        raw['reach'] = int(row.get('reach', 0))
        raw['impressions'] = int(row.get('impressions', 0))
        raw['link_clicks'] = int(row.get('inline_link_clicks', 0))
        for action in row.get('actions', []):
            t = action.get('action_type')
            v = int(action.get('value', 0))
            if t == 'landing_page_view': raw['lpv'] = v
            elif t == 'add_to_cart': raw['atc'] = v
            elif t == 'initiate_checkout': raw['chk'] = v
            elif t == 'add_payment_info': raw['pay'] = v
            elif t == 'purchase': raw['pur'] = v

    # Calculate
    cpm = (raw['spend'] / raw['impressions']) * 1000 if raw['impressions'] else 0
    ctr = (raw['link_clicks'] / raw['impressions']) * 100 if raw['impressions'] else 0
    cpc = raw['spend'] / raw['link_clicks'] if raw['link_clicks'] else 0
    freq = raw['impressions'] / raw['reach'] if raw['reach'] else 0
    cpp = raw['spend'] / raw['pur'] if raw['pur'] else 0

    lpv_rate = (raw['lpv'] / raw['link_clicks']) * 100 if raw['link_clicks'] else 0
    atc_rate = (raw['atc'] / raw['lpv']) * 100 if raw['lpv'] else 0
    chk_rate = (raw['chk'] / raw['atc']) * 100 if raw['atc'] else 0
    pur_rate = (raw['pur'] / raw['chk']) * 100 if raw['chk'] else 0

    # Diagnostic Logic
    recs = []
    if freq > 3.0: recs.append("🟡 <strong>Creative Fatigue:</strong> Frequency is over 3. Refresh creatives.")
    if cpm > 400: recs.append("🔴 <strong>High CPM:</strong> Audience is too narrow or competition is fierce.")
    if raw['link_clicks'] > 0 and lpv_rate < 60: recs.append(f"🔴 <strong>Traffic Drop-off:</strong> Low Landing Page Views ({lpv_rate:.1f}% load rate). <strong>Action:</strong> Check site speed.")
    elif raw['lpv'] > 0 and atc_rate < 3: recs.append(f"🟡 <strong>Low Intent:</strong> Low add-to-cart rate ({atc_rate:.1f}%). <strong>Action:</strong> Check product offer/pricing.")
    elif raw['atc'] > 0 and chk_rate < 50: recs.append(f"🔴 <strong>Cart Abandonment:</strong> Low checkout initiation ({chk_rate:.1f}%). <strong>Action:</strong> Check shipping costs.")
    elif raw['chk'] > 0 and pur_rate < 50: recs.append("🟡 <strong>Payment Friction:</strong> Users start checkout but don't finish. Check payment gateways.")
    
    if not recs and raw['spend'] > 0: recs.append("🟢 <strong>Healthy Funnel:</strong> Metrics are stable. Let it optimize.")
    elif raw['spend'] == 0: recs.append("⚪ <strong>No Spend Detected:</strong> Ensure campaigns are active and delivering.")

    # Format for JSON payload
    all_data[period] = {
        'date_display': f"{start_date.strftime('%d/%m/%Y')} &rarr; {end_date.strftime('%d/%m/%Y')}",
        'recommendations_html': "".join([f"<div class='rec-item'>{r}</div>" for r in recs]),
        'spend_val': f"₹{raw['spend']:.0f}",
        'spend_table': f"₹{raw['spend']:.2f}",
        'reach_val': f"{raw['reach']:,}",
        'impressions_val': f"{raw['impressions']:,}",
        'freq_val': f"{freq:.2f}x",
        'freq_badge': get_status(freq < 3.0),
        'cpm_val': f"₹{cpm:.0f}",
        'cpm_table': f"₹{cpm:.2f}",
        'cpm_badge': get_status(150 <= cpm <= 400),
        'clicks_val': f"{raw['link_clicks']:,}",
        'ctr_val': f"{ctr:.2f}%",
        'ctr_badge': get_status(ctr > 1.0),
        'cpc_val': f"₹{cpc:.2f}",
        'cpc_badge': get_status(cpc < 15.0),
        'pur_val': f"{raw['pur']}",
        'pur_badge': get_status(raw['pur'] > 0),
        'cpp_val': f"₹{cpp:.0f}",
        'lpv_val': f"{raw['lpv']:,}",
        'lpv_rate_val': f"{lpv_rate:.2f}%",
        'lpv_badge': get_status(lpv_rate > 60.0),
        'lpv_width': f"{min(100, lpv_rate)}%",
        'atc_val': f"{raw['atc']}",
        'atc_rate_val': f"{atc_rate:.2f}%",
        'atc_badge': get_status(atc_rate > 3.0),
        'atc_width': f"{min(100, atc_rate)}%",
        'chk_val': f"{raw['chk']}",
        'chk_rate_val': f"{chk_rate:.0f}%",
        'chk_badge': get_status(chk_rate > 50.0, bad_text="Watch", watch=True),
        'chk_width': f"{min(100, chk_rate)}%",
        'pay_val': f"{raw['pay']}",
        'pur_rate_val': f"{pur_rate:.2f}%",
        'pur_width': f"{min(100, pur_rate)}%",
    }

json_data = json.dumps(all_data)

# 4. GENERATE HTML WITH EMBEDDED JS
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One Good Object | Dashboard</title>
    <style>
        :root {{ --bg-dark: #0d0d0d; --card-bg: #141414; --border-color: #2a2a2a; --text-main: #f5f5f5; --text-muted: #888; --brand-yellow: #ffb800; --success-green: #00e676; --danger-red: #ff3d00; --warning-orange: #ff9100; }}
        body {{ font-family: 'SF Mono', 'Roboto Mono', Consolas, monospace; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 30px; font-size: 13px; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 16px; font-weight: normal; }}
        .header h1 span {{ color: var(--text-muted); font-size: 12px; display: block; margin-top: 5px; }}
        .badge-live {{ border: 1px solid var(--success-green); color: var(--success-green); padding: 4px 10px; border-radius: 20px; font-size: 12px; }}
        
        .controls-wrapper {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }}
        .date-section {{ display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }}
        .date-label {{ color: var(--text-muted); letter-spacing: 1px; }}
        .date-display {{ background: var(--bg-dark); border: 1px solid var(--border-color); padding: 8px 15px; border-radius: 6px; color: var(--brand-yellow); }}
        
        .preset-btns {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .preset-btn {{ background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 6px 12px; border-radius: 20px; cursor: pointer; font-family: inherit; font-size: 12px; transition: 0.2s; }}
        .preset-btn:hover {{ border-color: var(--text-muted); }}
        .preset-btn.active {{ border-color: var(--brand-yellow); color: var(--brand-yellow); }}
        
        h2 {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 20px; font-weight: normal; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 40px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; }}
        .card-title {{ font-size: 12px; color: var(--text-muted); margin-bottom: 15px; }}
        .card-value {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .card-sub {{ font-size: 11px; color: var(--text-muted); }}
        .text-green {{ color: var(--success-green); }}
        .text-yellow {{ color: var(--brand-yellow); }}
        
        .funnel-container {{ display: flex; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 40px; }}
        .funnel-step {{ flex: 1; padding: 25px 20px; border-right: 1px solid var(--border-color); }}
        .funnel-step:last-child {{ border-right: none; }}
        .f-title {{ font-size: 10px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 15px; letter-spacing: 1px; }}
        .f-value {{ font-size: 20px; font-weight: bold; margin-bottom: 5px; }}
        .f-percent {{ font-size: 11px; color: var(--text-muted); margin-bottom: 20px; height: 15px; }}
        .progress-bar {{ height: 2px; background: #333; width: 100%; }}
        .progress-fill {{ height: 100%; background: var(--brand-yellow); transition: width 0.5s ease; }}
        .fill-green {{ background: var(--success-green); }}
        
        .table-container {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow-x: auto; margin-bottom: 40px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th, td {{ padding: 18px 20px; border-bottom: 1px solid var(--border-color); }}
        th {{ color: var(--text-muted); font-size: 11px; font-weight: normal; text-transform: uppercase; letter-spacing: 1px; }}
        tr:last-child td {{ border-bottom: none; }}
        .col-metric {{ color: var(--text-muted); }}
        .col-value {{ font-weight: bold; }}
        .col-bench {{ color: var(--text-muted); }}
        .col-notes {{ color: var(--text-muted); font-size: 11px; }}
        
        .badge {{ padding: 4px 10px; border-radius: 20px; font-size: 11px; white-space: nowrap; }}
        .badge-good {{ background: rgba(0, 230, 118, 0.1); color: var(--success-green); }}
        .badge-watch {{ background: rgba(255, 145, 0, 0.1); color: var(--warning-orange); }}
        .badge-bad {{ background: rgba(255, 61, 0, 0.1); color: var(--danger-red); }}
        .badge-none {{ color: var(--text-muted); }}

        .recommendation-box {{ background: rgba(255, 184, 0, 0.05); border: 1px solid var(--brand-yellow); border-radius: 8px; padding: 20px; margin-bottom: 40px; line-height: 1.6; }}
        .recommendation-box h3 {{ margin-top: 0; color: var(--brand-yellow); font-size: 14px; text-transform: uppercase; }}
        .rec-item {{ margin-bottom: 8px; }}
        
        @media (max-width: 1000px) {{ .funnel-container {{ flex-direction: column; }} .funnel-step {{ border-right: none; border-bottom: 1px solid var(--border-color); }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>One Good Object<span>Meta Ads Dashboard</span></h1>
        <div class="badge-live">Live Data Active</div>
    </div>

    <div class="controls-wrapper">
        <div class="date-section">
            <span class="date-label">DATE RANGE</span>
            <div class="date-display" id="date_display">Loading...</div>
            <div class="preset-btns">
                <button class="preset-btn" id="btn-today" onclick="updateView('today')">Today</button>
                <button class="preset-btn active" id="btn-yesterday" onclick="updateView('yesterday')">Yesterday</button>
                <button class="preset-btn" id="btn-last_2_days" onclick="updateView('last_2_days')">Last 2 Days</button>
                <button class="preset-btn" id="btn-last_3_days" onclick="updateView('last_3_days')">Last 3 Days</button>
                <button class="preset-btn" id="btn-last_7_days" onclick="updateView('last_7_days')">Last 7 Days</button>
                <button class="preset-btn" id="btn-last_30_days" onclick="updateView('last_30_days')">Last 30 Days</button>
            </div>
        </div>
    </div>

    <div class="recommendation-box">
        <h3>Daily AI Diagnostic</h3>
        <div id="recommendations_html"></div>
    </div>

    <h2>Performance Overview</h2>
    <div class="grid">
        <div class="card" style="border-color: var(--brand-yellow); background: rgba(255,184,0,0.02);">
            <div class="card-title">Amount Spent</div><div class="card-value text-yellow" id="spend_val">-</div><div class="card-sub">Total ad spend</div>
        </div>
        <div class="card"><div class="card-title">Reach</div><div class="card-value" id="reach_val">-</div><div class="card-sub">Unique accounts</div></div>
        <div class="card"><div class="card-title">Impressions</div><div class="card-value" id="impressions_val">-</div><div class="card-sub">Freq: <span id="freq_val_sub">-</span></div></div>
        <div class="card"><div class="card-title">CPM</div><div class="card-value" id="cpm_val">-</div><div class="card-sub">Cost per 1K impressions</div></div>
        <div class="card"><div class="card-title">Link Clicks</div><div class="card-value" id="clicks_val">-</div><div class="card-sub">All clicks</div></div>
        <div class="card"><div class="card-title">CTR</div><div class="card-value text-green" id="ctr_val">-</div><div class="card-sub">Link click-through rate</div></div>
        <div class="card"><div class="card-title">CPC</div><div class="card-value" id="cpc_val">-</div><div class="card-sub">Cost per link click</div></div>
        <div class="card"><div class="card-title">Purchases</div><div class="card-value text-green" id="pur_val_top">-</div><div class="card-sub">Website purchases</div></div>
    </div>

    <h2>Conversion Funnel</h2>
    <div class="funnel-container">
        <div class="funnel-step"><div class="f-title">Impressions</div><div class="f-value" id="impressions_val_f">-</div><div class="f-percent">100%</div><div class="progress-bar"><div class="progress-fill" style="width: 100%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Landing Views</div><div class="f-value" id="lpv_val">-</div><div class="f-percent"><span id="lpv_rate_val_f">-</span> of clicks</div><div class="progress-bar"><div class="progress-fill" id="lpv_width" style="width: 0%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Add to Cart</div><div class="f-value" id="atc_val">-</div><div class="f-percent"><span id="atc_rate_val_f">-</span> of views</div><div class="progress-bar"><div class="progress-fill" id="atc_width" style="width: 0%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Checkout</div><div class="f-value" id="chk_val">-</div><div class="f-percent"><span id="chk_rate_val_f">-</span> of cart</div><div class="progress-bar"><div class="progress-fill" id="chk_width" style="width: 0%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Payment Info</div><div class="f-value" id="pay_val">-</div><div class="f-percent">-</div><div class="progress-bar"><div class="progress-fill" style="width: 100%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Purchases</div><div class="f-value" id="pur_val">-</div><div class="f-percent"><span id="pur_rate_val_f">-</span> of checkout</div><div class="progress-bar"><div class="progress-fill fill-green" id="pur_width" style="width: 0%;"></div></div></div>
    </div>

    <h2>Full Breakdown</h2>
    <div class="table-container">
        <table>
            <thead><tr><th>Metric</th><th>Value</th><th>Benchmark</th><th>Status</th><th>Notes</th></tr></thead>
            <tbody>
                <tr><td class="col-metric">Impressions</td><td class="col-value" id="impressions_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Total times ads were shown</td></tr>
                <tr><td class="col-metric">Reach</td><td class="col-value" id="reach_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Unique accounts that saw the ad</td></tr>
                <tr><td class="col-metric">Frequency</td><td class="col-value text-green" id="freq_val">-</td><td class="col-bench">&lt; 3x</td><td id="freq_badge">-</td><td class="col-notes">Healthy frequency</td></tr>
                <tr><td class="col-metric">Link Clicks</td><td class="col-value" id="clicks_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Clicks to your website</td></tr>
                <tr><td class="col-metric">CTR (Link)</td><td class="col-value text-green" id="ctr_val_t">-</td><td class="col-bench">&gt; 1%</td><td id="ctr_badge">-</td><td class="col-notes">Strong click-through rate</td></tr>
                <tr><td class="col-metric">CPC</td><td class="col-value text-green" id="cpc_val_t">-</td><td class="col-bench">&lt; ₹15</td><td id="cpc_badge">-</td><td class="col-notes">Cost per click</td></tr>
                <tr><td class="col-metric">CPM</td><td class="col-value text-green" id="cpm_table">-</td><td class="col-bench">₹150-400</td><td id="cpm_badge">-</td><td class="col-notes">Cost to reach 1,000 people</td></tr>
                <tr><td class="col-metric">Landing Page Views</td><td class="col-value" id="lpv_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">People who loaded your landing page</td></tr>
                <tr><td class="col-metric">LPV Rate</td><td class="col-value" id="lpv_rate_val">-</td><td class="col-bench">&gt; 60%</td><td id="lpv_badge">-</td><td class="col-notes">Landing page load rate vs clicks</td></tr>
                <tr><td class="col-metric">Add to Cart</td><td class="col-value" id="atc_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Products added to cart</td></tr>
                <tr><td class="col-metric">ATC Rate</td><td class="col-value text-green" id="atc_rate_val">-</td><td class="col-bench">&gt; 3%</td><td id="atc_badge">-</td><td class="col-notes">Add-to-cart rate from landing page views</td></tr>
                <tr><td class="col-metric">Checkouts Initiated</td><td class="col-value" id="chk_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Users who started checkout</td></tr>
                <tr><td class="col-metric">Checkout Rate</td><td class="col-value" id="chk_rate_val">-</td><td class="col-bench">&gt; 50%</td><td id="chk_badge">-</td><td class="col-notes">Checkout rate from cart adds</td></tr>
                <tr><td class="col-metric">Payment Info Added</td><td class="col-value" id="pay_val_t">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Users who entered payment details</td></tr>
                <tr><td class="col-metric">Purchases</td><td class="col-value text-green" id="pur_val_t">-</td><td class="col-bench">-</td><td id="pur_badge">-</td><td class="col-notes">Completed website purchases</td></tr>
                <tr><td class="col-metric">Cost per Purchase</td><td class="col-value" id="cpp_val">-</td><td class="col-bench">Depends on AOV</td><td><span class="badge-none">-</span></td><td class="col-notes">Total spend &divide; purchases</td></tr>
                <tr><td class="col-metric">Amount Spent</td><td class="col-value" id="spend_table">-</td><td class="col-bench">-</td><td><span class="badge-none">-</span></td><td class="col-notes">Total ad spend for period</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        // Inject Python data into Javascript
        const dashData = {json_data};

        function updateView(period) {{
            // Update Active Button UI
            document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + period).classList.add('active');

            const d = dashData[period];
            if(!d) return;

            // Loop through all data keys and update the corresponding HTML elements
            for (const [key, value] of Object.entries(d)) {{
                const el = document.getElementById(key);
                if (el) {{
                    if (key.includes('width')) {{
                        el.style.width = value;
                    }} else {{
                        el.innerHTML = value;
                    }}
                }}
                
                // Handle duplicate elements needed in multiple places
                if(key === 'freq_val') document.getElementById('freq_val_sub').innerHTML = value;
                if(key === 'impressions_val') {{ document.getElementById('impressions_val_f').innerHTML = value; document.getElementById('impressions_val_t').innerHTML = value; }}
                if(key === 'clicks_val') document.getElementById('clicks_val_t').innerHTML = value;
                if(key === 'ctr_val') document.getElementById('ctr_val_t').innerHTML = value;
                if(key === 'cpc_val') document.getElementById('cpc_val_t').innerHTML = value;
                if(key === 'lpv_val') document.getElementById('lpv_val_t').innerHTML = value;
                if(key === 'lpv_rate_val') document.getElementById('lpv_rate_val_f').innerHTML = value;
                if(key === 'atc_val') document.getElementById('atc_val_t').innerHTML = value;
                if(key === 'atc_rate_val') document.getElementById('atc_rate_val_f').innerHTML = value;
                if(key === 'chk_val') document.getElementById('chk_val_t').innerHTML = value;
                if(key === 'chk_rate_val') document.getElementById('chk_rate_val_f').innerHTML = value;
                if(key === 'pay_val') document.getElementById('pay_val_t').innerHTML = value;
                if(key === 'pur_val') {{ document.getElementById('pur_val_top').innerHTML = value; document.getElementById('pur_val_t').innerHTML = value; }}
                if(key === 'pur_rate_val') document.getElementById('pur_rate_val_f').innerHTML = value;
                if(key === 'reach_val') document.getElementById('reach_val_t').innerHTML = value;
            }}
        }}

        // Load Yesterday's data by default on page load
        updateView('yesterday');
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as file:
    file.write(html_content)
