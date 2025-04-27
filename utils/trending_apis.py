import requests
from pytrends.request import TrendReq

# Google Trends (Free)
def get_google_trends(niche, geo=''):  # geo='US' or '' for worldwide
    from pytrends.request import TrendReq
    pytrends = TrendReq()
    try:
        pytrends.build_payload([niche], cat=0, timeframe='now 7-d', geo=geo)
        related = pytrends.related_queries()
        if (
            related 
            and niche in related 
            and isinstance(related[niche], dict)
            and 'top' in related[niche]
            and related[niche]['top'] is not None
            and not related[niche]['top'].empty
        ):
            return [row['query'] for row in related[niche]['top'].to_dict('records')]
        else:
            print(f"[DIAG] No related queries found or empty DataFrame for: {niche}")
    except Exception as e:
        print(f"[DIAG] Google Trends error: {e}")
        return [f"ERROR: {e}"]
    return []

# YouTube Trends (Free tier, limited)
def get_youtube_trends(api_key, region_code='US', max_results=10):
    url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode={region_code}&maxResults={max_results}&key={api_key}'
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return [item['snippet']['title'] for item in data.get('items', [])]
    except Exception:
        return []

# Twitter/X Trends (Free: limited, Paid: more)
def get_twitter_trends(bearer_token, woeid=1):  # 1 = Worldwide
    url = f'https://api.twitter.com/1.1/trends/place.json?id={woeid}'
    headers = {'Authorization': f'Bearer {bearer_token}'}
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        trends = resp.json()[0]['trends']
        return [trend['name'] for trend in trends]
    except Exception:
        return []
