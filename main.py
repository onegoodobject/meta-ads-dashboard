import datetime
import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

# 1. AUTHENTICATE WITH SECRETS
app_id = os.environ.get('META_APP_ID')
app_secret = os.environ.get('META_APP_SECRET')
access_token = os.environ.get('META_ACCESS_TOKEN')
ad_account_id = os.environ.get('META_AD_ACCOUNT_ID')

FacebookAdsApi.init(app_id, app_secret, access_token)
account = AdAccount(ad_account_id)

# 2. FETCH YESTERDAY'S DATA
yesterday = datetime.date.today() - datetime.timedelta(days=1)
date_str = yesterday.strftime('%d-%m-%Y')
meta_date_str = yesterday.strftime('%Y-%m-%d')

params = {
    'time_range': {'since': meta_date_str, 'until': meta_date_str},
    'level': 'account',
}
fields = ['spend', 'reach', 'impressions', 'inline_link_clicks', 'actions']

try:
    insights = account.get_insights(fields=fields, params=params)
except Exception as e:
    print(f"Error fetching data: {e}")
    insights = []

# 3. PARSE THE DATA
data = {
    'spend': 0.0, 'reach': 0, 'impressions': 0, 'link_clicks': 0,
    'landing_page_views': 0, 'add_to_cart': 0, 'checkouts_initiated': 0, 
    'payment_info_added': 0, 'purchases': 0
}

if insights:
    row = insights[0]
    data['spend'] = float(row.get('spend', 0))
    data['reach'] = int(row.get('reach', 0))
    data['impressions'] = int(row.get('impressions', 0))
    data['link_clicks'] = int(row.get('inline_link_clicks', 0))
    
    actions = row.get('actions', [])
    for action in actions:
        action_type = action.get('action_type')
        value = int(action.get('value', 0))
        
        if action_type == 'landing_page_view': data['landing_page_views'] = value
        elif action_type == 'add_to_cart': data['add_to_cart'] = value
        elif action_type == 'initiate_checkout': data['checkouts_initiated'] = value
        elif action_type == 'add_payment_info': data['payment_info_added'] = value
        elif action_type == 'purchase': data['purchases'] = value

# 4. CALCULATE METRICS & FUNNEL
cpm = (data['spend'] / data['impressions']) * 1000 if data['impressions'] else 0
ctr = (data['link_clicks'] / data['impressions']) * 100 if data['impressions'] else 0
cpc = data['spend'] / data['link_clicks'] if data['link_clicks'] else 0
freq = data['impressions'] / data['reach'] if data['reach'] else 0

lpv_rate = (data['landing_page_views'] / data['link_clicks']) * 100 if data['link_clicks'] else 0
atc_rate = (data['add_to_cart'] / data['landing_page_views']) * 100 if data['landing_page_views'] else 0
checkout_rate = (data['checkouts_initiated'] / data['add_to_cart']) * 100 if data['add_to_cart'] else 0
purchase_rate = (data['purchases'] / data['checkouts_initiated']) * 100 if data['checkouts_initiated'] else 0

# 5. DIAGNOSTIC LOGIC
recommendations = []
if freq > 3.0: recommendations.append("🟡 <strong>Creative Fatigue:</strong> Frequency is over 3. Refresh creatives.")
if cpm > 400: recommendations.append("🔴 <strong>High CPM:</strong> Audience is too narrow or competition is fierce.")
if data['link_clicks'] > 0 and lpv_rate < 70: recommendations.append(f"🔴 <strong>Traffic Drop-off:</strong> High clicks but low Landing Page Views ({lpv_rate:.1f}% load rate). <strong>Action:</strong> Check site speed.")
elif data['landing_page_views'] > 0 and atc_rate < 5: recommendations.append(f"🟡 <strong>Low Intent:</strong> Low add-to-cart rate ({atc_rate:.1f}%). <strong>Action:</strong> Check product offer/pricing.")
elif data['add_to_cart'] > 0 and checkout_rate < 40: recommendations.append(f"🔴 <strong>Cart Abandonment:</strong> Low checkout initiation ({checkout_rate:.1f}%). <strong>Action:</strong> Ensure no hidden shipping costs.")
elif data['checkouts_initiated'] > 0 and purchase_rate < 50: recommendations.append("🟡 <strong>Payment Friction:</strong> Users start checkout but don't finish. Check payment gateways.")

if not recommendations and data['spend'] > 0: recommendations.append("🟢 <strong>Healthy Funnel:</strong> Metrics are stable. Let it optimize.")
elif data['spend'] == 0: recommendations.append("⚪ <strong>No Spend Detected:</strong> Ensure campaigns are active and delivering today.")

# 6. GENERATE HTML
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One Good Object | Dashboard</title>
    <style>
        :root {{ --bg-dark: #0d0d0d; --card-bg: #141414; --border-color: #2a2a2a; --text-main: #f5f5f5; --text-muted: #888; --brand-yellow: #ffb800; --success-green: #00e676; --danger-red: #ff3d00; --warning-orange: #ff9100; }}
        body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; display: flex; flex-direction: column; }}
        .header h1 span {{ font-size: 12px; color: var(--text-muted); font-weight: normal; margin-top: 4px; }}
        .status-badge {{ background: rgba(0, 230, 118, 0.1); color: var(--success-green); padding: 4px 10px; border-radius: 4px; font-size: 12px; border: 1px solid var(--success-green); }}
        .controls {{ display: flex; justify-content: space-between; background: var(--card-bg); padding: 15px; border-radius: 8px; margin-bottom: 30px; border: 1px solid var(--border-color); flex-wrap: wrap; gap: 15px; }}
        .date-range {{ display: flex; gap: 10px; align-items: center; color: var(--text-muted); font-size: 14px; }}
        .date-box {{ background: var(--bg-dark); border: 1px solid var(--border-color); padding: 8px 12px; border-radius: 4px; color: var(--text-main); }}
        .btn-yellow {{ background: var(--brand-yellow); color: #000; border: none; padding: 8px 20px; border-radius: 4px; font-weight: bold; cursor: pointer; }}
        h2 {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 15px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 40px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; }}
        .card-title {{ font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }}
        .card-value {{ font-size: 28px; font-weight: bold; margin-bottom: 5px; }}
        .card-sub {{ font-size: 12px; color: var(--text-muted); }}
        .value-yellow {{ color: var(--brand-yellow); }}
        .funnel-container {{ display: flex; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; margin-bottom: 40px; }}
        .funnel-step {{ flex: 1; padding: 20px; border-right: 1px solid var(--border-color); }}
        .funnel-step:last-child {{ border-right: none; }}
        .f-title {{ font-size: 10px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; }}
        .f-value {{ font-size: 22px; font-weight: bold; margin-bottom: 5px; }}
        .f-percent {{ font-size: 12px; color: var(--text-muted); margin-bottom: 15px; }}
        .progress-bar {{ height: 4px; background: #333; width: 100%; border-radius: 2px; }}
        .progress-fill {{ height: 100%; background: var(--brand-yellow); border-radius: 2px; }}
        .fill-green {{ background: var(--success-green); }}
        .recommendation-box {{ background: rgba(255, 184, 0, 0.05); border: 1px solid var(--brand-yellow); border-radius: 8px; padding: 20px; margin-bottom: 40px; }}
        .recommendation-box h3 {{ margin-top: 0; color: var(--brand-yellow); font-size: 16px; }}
        .rec-item {{ margin-bottom: 10px; font-size: 14px; line-height: 1.5; }}
        @media (max-width: 768px) {{ .funnel-container {{ flex-direction: column; }} .funnel-step {{ border-right: none; border-bottom: 1px solid var(--border-color); }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>One Good Object <span>Meta Ads Dashboard</span></h1>
        <div class="status-badge">Live Data Connected</div>
    </div>
    <div class="controls">
        <div class="date-range">DATE RANGE <div class="date-box">{date_str}</div> &rarr; <div class="date-box">{date_str}</div></div>
        <div><button class="btn-yellow">Analyze</button></div>
    </div>
    <div class="recommendation-box">
        <h3>🧠 Daily AI Diagnostic</h3>
        {"".join([f"<div class='rec-item'>{r}</div>" for r in recommendations])}
    </div>
    <h2>Performance Overview</h2>
    <div class="grid">
        <div class="card" style="border: 1px solid var(--brand-yellow); background: rgba(255,184,0,0.02);"><div class="card-title">Amount Spent</div><div class="card-value value-yellow">₹{data['spend']:.0f}</div><div class="card-sub">Total ad spend</div></div>
        <div class="card"><div class="card-title">Reach</div><div class="card-value">{data['reach']:,}</div><div class="card-sub">Unique accounts</div></div>
        <div class="card"><div class="card-title">Impressions</div><div class="card-value">{data['impressions']:,}</div><div class="card-sub">Freq: {freq:.2f}x</div></div>
        <div class="card"><div class="card-title">CPM</div><div class="card-value">₹{cpm:.0f}</div><div class="card-sub">Cost per 1K impressions</div></div>
        <div class="card"><div class="card-title">Link Clicks</div><div class="card-value">{data['link_clicks']:,}</div><div class="card-sub">All clicks</div></div>
        <div class="card"><div class="card-title">CTR</div><div class="card-value" style="color: var(--success-green);">{ctr:.2f}%</div><div class="card-sub">Link click-through rate</div></div>
        <div class="card"><div class="card-title">CPC</div><div class="card-value">₹{cpc:.2f}</div><div class="card-sub">Cost per link click</div></div>
        <div class="card"><div class="card-title">Purchases</div><div class="card-value" style="color: var(--success-green);">{data['purchases']}</div><div class="card-sub">Website purchases</div></div>
    </div>
    <h2>Conversion Funnel</h2>
    <div class="funnel-container">
        <div class="funnel-step"><div class="f-title">Impressions</div><div class="f-value">{data['impressions']:,}</div><div class="f-percent">100%</div><div class="progress-bar"><div class="progress-fill" style="width: 100%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Landing Views</div><div class="f-value">{data['landing_page_views']:,}</div><div class="f-percent">{lpv_rate:.1f}% of clicks</div><div class="progress-bar"><div class="progress-fill" style="width: {min(100, lpv_rate)}%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Add to Cart</div><div class="f-value">{data['add_to_cart']}</div><div class="f-percent">{atc_rate:.1f}% of views</div><div class="progress-bar"><div class="progress-fill" style="width: {min(100, atc_rate)}%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Checkout</div><div class="f-value">{data['checkouts_initiated']}</div><div class="f-percent">{checkout_rate:.1f}% of cart</div><div class="progress-bar"><div class="progress-fill" style="width: {min(100, checkout_rate)}%;"></div></div></div>
        <div class="funnel-step"><div class="f-title">Purchases</div><div class="f-value">{data['purchases']}</div><div class="f-percent">{purchase_rate:.1f}% of checkout</div><div class="progress-bar"><div class="progress-fill fill-green" style="width: {min(100, purchase_rate)}%;"></div></div></div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as file:
    file.write(html_content)
