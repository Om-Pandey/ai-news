import json
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from app import create_app
from app.db import get_db
from app.auth import bp as auth_bp
from datetime import datetime
from app.category_sentiment import calculate_and_save_category_sentiments

app = create_app()

category_sentiments_file = 'app/category_sentiments.json'
categories = [
    'Strategic Innovations, Evolving Technologies, and Competition',
    'Regulatory Changes and Continued Regulatory Scrutiny',
    'Resiliency and Cybersecurity',
    'Geopolitical and Macroeconomic Uncertainty',
    'Human Capital',
    'Interconnectedness Risk and Externalization of Services and Support'
]
calculate_and_save_category_sentiments('app/final_result.json', category_sentiments_file, categories)

with open('app/final_result.json', 'r') as f:
    final_result = json.load(f)

with open(category_sentiments_file, 'r') as f:
    category_sentiments = json.load(f)

def extract_date_from_url(url):
    match = re.search(r'/(\d{4}/\d{2}/\d{2})/', url)
    if match:
        return match.group(1).replace('/', '-')
    return 'No Date'

def format_score(score):
    try:
        return round(float(score), 4)
    except (TypeError, ValueError):
        return 0.0

# Extract hot topics from the loaded data
def get_hot_topics(data, categories, top_n=3):
    articles = [article for sublist in data['articles'].values() for article in sublist]

    # Create a dictionary to hold the highest scored articles per category
    category_articles = {category: [] for category in categories}

    # Sort articles by score in descending order
    sorted_articles = sorted(articles, key=lambda x: format_score(x.get('score', 0)), reverse=True)

    # Fill the category_articles dictionary with top_n articles for each category
    for article in sorted_articles:
        article_categories = article.get('category', "").split("\n")
        for cat in article_categories:
            if cat in category_articles and len(category_articles[cat]) < top_n:
                category_articles[cat].append(article)
    
    hot_topics = []
    
    for category in categories:
        daily_scores = category_sentiments.get(category, {}).get('daily_average_scores', {})
        latest_date = max(daily_scores.keys(), default='No Date')
        latest_score = format_score(daily_scores.get(latest_date, 0)) if latest_date != 'No Date' else 0.0
        top_articles = category_articles[category]

        # Ensure each category has exactly top_n articles
        while len(top_articles) < top_n:
            top_articles.append({'title': 'No Article', 'url': '#', 'score': 0.0})

        hot_topics.append({
            'category': category,
            'latest_score': latest_score,
            'articles': [{
                **article,
                'score': format_score(article.get('score', 0))  # Ensure score is formatted to 4 decimal places
            } for article in top_articles]
        })

    return hot_topics
    

@app.route('/')
def index():
    if g.user is None:
        return redirect(url_for('auth.login'))

    
    news_summary = []
    for date in final_result['articles']:
        for news in final_result['articles'][date]:
            published_date = extract_date_from_url(news.get('url', ''))
            news_summary.append({
                'headline': news.get('title', 'No Title'),
                'summary': news.get('description', 'No Description'),
                'url': news.get('url', '#'),
                'published': published_date,
                'source': news.get('source', 'No Source'),
                'score': format_score(news.get('score', 0)),
                'category': news.get('category', 'No Category')
            })

    news_summary.sort(key=lambda x: datetime.strptime(x['published'], '%Y-%m-%d') if x['published'] != 'No Date' else datetime.min, reverse=True)
    news_summary = news_summary[:3]

    market_sentiment = []
    for idx, category in enumerate(categories, start=1):
        daily_scores = category_sentiments[category]['daily_average_scores']
        latest_date = max(daily_scores.keys(), default='No Date')
        latest_score = daily_scores.get(latest_date, 0) if latest_date != 'No Date' else 0.0
        history_score = category_sentiments[category]['history_average_score']
        market_sentiment.append({
            'id': idx,
            'topic': category,
            'score': history_score,
            'latest_date': latest_date,
            'latest_score': latest_score,
            'keywords': ['#keyword 1', '#keyword 2', '#keyword 3']
        })

    hot_topics = get_hot_topics(final_result, categories)

    return render_template('index.html', news_summary=news_summary, market_sentiment=market_sentiment, hot_topics=hot_topics)

@app.route('/more_news', methods=['GET', 'POST'])
def more_news():
    query = request.form.get('query')
    filtered_articles = [article for date in final_result['articles'] for article in final_result['articles'][date]]
    if query:
        filtered_articles = [article for article in filtered_articles if query.lower() in article['title'].lower()]

    news_summary = []
    for news in filtered_articles:
        published_date = extract_date_from_url(news.get('url', ''))
        news_summary.append({
            'headline': news.get('title', 'No Title'),
            'summary': news.get('description', 'No Description'),
            'url': news.get('url', '#'),
            'published': published_date,
            'source': news.get('source', 'No Source'),
            'score': news.get('score', 'No Score'),
            'category': news.get('category', 'No Category')
        })

    news_summary.sort(key=lambda x: datetime.strptime(x['published'], '%Y-%m-%d') if x['published'] != 'No Date' else datetime.min, reverse=True)

    return render_template('more_news.html', news_summary=news_summary, query=query)

@app.route('/detail/news/<int:item_id>')
def news_detail(item_id):
    date_keys = list(final_result['articles'].keys())
    article = None
    for date in date_keys:
        if item_id <= len(final_result['articles'][date]):
            article = final_result['articles'][date][item_id - 1]
            break
        item_id -= len(final_result['articles'][date])
    
    if article is None:
        return "Article not found", 404

    item_detail = {
        'headline': article['title'],
        'summary': article['description'],
        'url': article['url'],
        'published': extract_date_from_url(article['url'])
    }
    return render_template('news_detail.html', item=item_detail)

@app.route('/detail/market/<int:item_id>')
def market_detail(item_id):
    with open('app/category_sentiments.json', 'r') as f:
        category_sentiments = json.load(f)

    category = categories[item_id - 1]
    item = {
        'topic': category,
        'history_score': category_sentiments[category]['history_average_score'],
        'daily_scores': category_sentiments[category]['daily_average_scores']
    }

    return render_template('market_detail.html', item=item)

@app.route('/detail/hot/<int:item_id>')
def hot_topic_detail(item_id):
    hot_topics = get_hot_topics(final_result, categories)
    if 1 <= item_id <= len(hot_topics):
        item = hot_topics[item_id - 1]
    else:
        item = None
    return render_template('hot_topic_detail.html', item=item)

@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT id, username, password, access_level FROM user WHERE id = ?',
            (user_id,)
        ).fetchone()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


app.register_blueprint(auth_bp, url_prefix='/auth', name='auth_blueprint')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
