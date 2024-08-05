import json
from datetime import datetime
from collections import defaultdict
import re

def extract_date_from_url(url):
    match = re.search(r'/(\d{4}/\d{2}/\d{2})/', url)
    if match:
        return match.group(1).replace('/', '-')
    return 'No Date'

def calculate_and_save_category_sentiments(input_file, output_file, categories):
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Initialize category sentiments data structure
    category_sentiments = {category: {"daily_average_scores": {}, "history_average_score": 0} for category in categories}

    # Process each article
    for date, articles in data['articles'].items():
        for article in articles:
            url = article.get('url', '')
            date = article.get('published', extract_date_from_url(url))
            if date == 'No Date':
                continue
            
            score = round(float(article.get('score', 0)), 4)
            article_categories = article.get('category', "").split("\n")

            for category in article_categories:
                if category in category_sentiments:
                    if date not in category_sentiments[category]["daily_average_scores"]:
                        category_sentiments[category]["daily_average_scores"][date] = []

                    category_sentiments[category]["daily_average_scores"][date].append(score)

    # Calculate daily average scores and keep four decimal places
    for category in category_sentiments:
        daily_scores = category_sentiments[category]["daily_average_scores"]
        sorted_daily_scores = {}
        for date in sorted(daily_scores.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d')):
            scores = daily_scores[date]
            sorted_daily_scores[date] = round(sum(scores) / len(scores), 4) if scores else 0.0
        category_sentiments[category]["daily_average_scores"] = sorted_daily_scores
        
        # Calculate history average score
        all_scores = [score for scores in sorted_daily_scores.values() for score in (scores if isinstance(scores, list) else [scores])]
        category_sentiments[category]["history_average_score"] = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

    # Save results to file
    with open(output_file, 'w') as f:
        json.dump(category_sentiments, f, indent=4)

if __name__ == "__main__":
    categories = [
        'Strategic Innovations, Evolving Technologies, and Competition',
        'Regulatory Changes and Continued Regulatory Scrutiny',
        'Resiliency and Cybersecurity',
        'Geopolitical and Macroeconomic Uncertainty',
        'Human Capital',
        'Interconnectedness Risk and Externalization of Services and Support'
    ]
    calculate_and_save_category_sentiments('app/final_result.json', 'app/category_sentiments.json', categories)
