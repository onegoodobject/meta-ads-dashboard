import datetime
import os
# from facebook_business.api import FacebookAdsApi
# from facebook_business.adobjects.adaccount import AdAccount

# 1. KPI RULES
TARGET_CPA = 500
TARGET_ROAS = 2.0
MIN_ORDERS = 2

# 2. FETCH DATA (Placeholder logic for your Meta API setup)
# In production, you would authenticate and pull from Meta here using os.environ.get('META_ACCESS_TOKEN')
yesterday = datetime.date.today() - datetime.timedelta(days=1)
print("Fetching Meta Ads Data...")

# MOCK DATA representing your campaigns
campaign_data = [
    {'name': 'Adv+ Shopping - Broad', 'spend': 1200, 'purchases': 3, 'revenue': 3000, 'ctr': 2.5},
    {'name': 'Retargeting - 30D', 'spend': 800, 'purchases': 1, 'revenue': 900, 'ctr': 1.8},
    {'name': 'Lookalike - 1% Purchasers', 'spend': 1500, 'purchases': 0, 'revenue': 0, 'ctr': 0.9},
]

# 3. ANALYSIS LOGIC
kill_list, scale_list, tweak_list = "", "", ""

for ad in campaign_data:
    name = ad['name']
    spend = ad['spend']
    purchases = ad['purchases']
    revenue = ad['revenue']
    ctr = ad['ctr']
    
    # Calculate live metrics safely
    cpa = spend / purchases if purchases > 0 else spend
    roas = revenue / spend if spend > 0 else 0

    # SCALE: Hitting all KPIs (>= 2 orders, CPA <= 500, ROAS >= 2.0)
    if purchases >= MIN_ORDERS and cpa <= TARGET_CPA and roas >= TARGET_ROAS:
        scale_list += f"""<div class='card scale'>
            <h3>🟢 Scale: {name}</h3>
            <p><strong>CPA:</strong> ₹{cpa:.2f} | <strong>ROAS:</strong> {roas:.2f}x | <strong>Orders:</strong> {purchases}</p>
            <p class='action'>Recommendation: Increase daily budget by 15-20%.</p>
        </div>"""
    
    # KILL: High Spend, No/Low Orders or Terrible ROAS
    elif (spend > TARGET_CPA * 1.5 and purchases < MIN_ORDERS) or (roas > 0 and roas < 1.0):
        kill_list += f"""<div class='card kill'>
            <h3>🔴 Kill: {name}</h3>
            <p><strong>CPA:</strong> ₹{cpa:.2f} | <strong>ROAS:</strong> {roas:.2f}x | <strong>Orders:</strong> {purchases}</p>
            <p class='action'>Recommendation: Turn off immediately. Bleeding budget.</p>
        </div>"""
        
    # TWEAK: Getting traffic but missing KPI thresholds
    else:
        tweak_list += f"""<div class='card tweak'>
            <h3>🟡 Tweak: {name}</h3>
            <p><strong>CPA:</strong> ₹{cpa:.2f} | <strong>ROAS:</strong> {roas:.2f}x | <strong>Orders:</strong> {purchases} | <strong>CTR:</strong> {ctr}%</p>
            <p class='action'>Recommendation: Watch closely. Try refreshing ad creative.</p>
        </div>"""

# 4. MOBILE-FRIENDLY HTML DASHBOARD
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Meta Ads Brain</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background-color: #f0f2f5; margin: 0; padding: 15px; color: #1c1e21; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 24px; color: #1877f2; }}
        .header p {{ margin: 5px 0 0 0; font-size: 14px; color: #65676b; }}
        .card {{ background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ margin: 0 0 10px 0; font-size: 18px; }}
        .card p {{ margin: 5px 0; font-size: 15px; }}
        .action {{ font-weight: bold; margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }}
        .kill {{ border-left: 6px solid #e41e3f; }}
        .scale {{ border-left: 6px solid #31a24c; }}
        .tweak {{ border-left: 6px solid #f5a623; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Ad Performance Brain</h1>
        <p>Updated: {yesterday.strftime('%b %d, %Y')}</p>
    </div>
    
    {scale_list if scale_list else "<div class='card'><p>No campaigns ready to scale today.</p></div>"}
    {kill_list if kill_list else "<div class='card'><p>No campaigns need killing today.</p></div>"}
    {tweak_list if tweak_list else "<div class='card'><p>No campaigns require tweaking today.</p></div>"}
</body>
</html>
"""

# Save as index.html so GitHub Pages can serve it
with open("index.html", "w", encoding="utf-8") as file:
    file.write(html_content)

print("HTML Dashboard Generated Successfully.")
