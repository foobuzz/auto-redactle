import csv
import json
import math
import random
import os
import string
import sys
import time
import urllib.parse
from pathlib import Path

import fire
import numpy as np
import requests
import sklearn.tree
import wikipediaapi
from bs4 import BeautifulSoup, SoupStrainer


USER_AGENT = "AutoRedactle/0.1 (https://github.com/foobuzz/auto-redactle)"


def save_wikidata_ids(ids_fn='wikidata_ids.csv'):
    url = "https://meta.wikimedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": "List_of_articles_every_Wikipedia_should_have/Expanded",
        "format": "json"
    }

    response = requests.get(url, params=params)
    html = response.json()['parse']['text']['*']

    with open('wikidata_ids.csv', 'w') as f:
        writer = csv.writer(f)
        for link in BeautifulSoup(
            html, 'html.parser', parse_only=SoupStrainer('a')
        ):
            if (link.has_attr('href')
                and link['href'].startswith('https://www.wikidata.org/wiki/Q')
            ):
                writer.writerow([link.get_text().strip(), link['href']])


def save_wikipedia_urls(ids_fn='wikidata_ids.csv', urls_fn='urls.csv'):
    ids = []
    with open(ids_fn) as f:
        reader = csv.reader(f)
        for row in reader:
            _, a_id = row
            ids.append(a_id)

    with open(urls_fn, 'a') as f:
        writer = csv.writer(f)
        for i, a_id in enumerate(ids):
            print(a_id)
            # Extracting the entity ID from the URL
            entity_id = a_id.split("/")[-1]

            # Get the Wikipedia title from Wikidata using the API
            wikidata_url = (
                f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
            )
            response = requests.get(wikidata_url)
            entity_data = response.json()
            
            # Extract the Wikipedia title in English
            sitelinks = entity_data['entities'][entity_id]['sitelinks']
            enwiki_url = sitelinks.get('enwiki', {}).get('url')
            writer.writerow([enwiki_url])


def fetch_urls(urls_fn='urls.csv'):
    save_wikidata_ids()
    save_wikipedia_urls(urls_fn=urls_fn)


def save_articles(urls_fn='urls.csv', folder='articles'):
    urls = []
    with open('urls.csv') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0]:
                urls.append(row[0])

    for i, url in enumerate(urls):
        url = urllib.parse.unquote(url.split("/wiki/")[-1])
        filename = url.replace('/', '%2F')

        path = Path(folder) / filename

        if path.exists():
            with path.open() as f:
                if f.read().strip() != '':
                    continue

        print(i+1, url)

        wiki_wiki = wikipediaapi.Wikipedia(USER_AGENT)
        page = wiki_wiki.page(url)
        with path.open('w') as f:
            f.write(page.text)


def build_index(folder='articles', dictionary_fname='top_1k_nouns.txt'):
    words_to_index = sorted(list(
        load_words(dictionary_fname)
        - load_words('redactle-common-words.txt')
    ))

    index_by_word = {
        w: i for i, w in enumerate(words_to_index)
    }

    index = {
        ':words': words_to_index,
    }

    for i, article_name in enumerate(os.listdir(folder)):
        if i%100 == 0:
            print(i)

        with open(f'{folder}/{article_name}') as f:
            content = f.read()

        memberships = []
        words = set(w.lower().strip(string.punctuation) for w in content.split())
        for w in words_to_index:
            if w in words:
                memberships.append(index_by_word[w])

        index[urllib.parse.unquote(article_name)] = memberships

    with open('index.json', 'w') as f:
        json.dump(index, f)


def load_words(filename):
    with open(filename) as f:
        return set(line.strip() for line in f if line.strip())


def build_decision_tree(
    index, articles, max_depth=None, debug_tree=True
):
    feature_names = index[':words']

    X = []
    Y = []
    for article, memberships in index.items():
        if article not in articles:
            continue

        memberships = set(memberships)
        features = []
        for word_index, word in enumerate(feature_names):
            features.append(word_index in memberships)

        X.append(features)
        Y.append(article)

    tree = sklearn.tree.DecisionTreeClassifier(max_depth=max_depth)
    tree.fit(X, Y)

    if debug_tree:
        with open('tree.txt', 'w') as f:
            f.write(
                sklearn.tree.export_text(
                    tree, feature_names=feature_names, max_depth=(max_depth or 1024),
                )
            )
        
    return tree, feature_names


def get_compatible_articles(index, redacted_title):
    target_pattern = [len(w) for w in redacted_title.split(' ')]

    if redacted_title == '':
        return set(index.keys())

    compatible_articles = set()
    for key in index:
        candidate_pattern = [len(w) for w in key.split('_')]
        if candidate_pattern == target_pattern:
            compatible_articles.add(key)

    return compatible_articles


def navigate_decision_tree(tree, feature_names):
    print("Please type the number of matches of the following words:")

    current_node = 0
    while True:
        word = feature_names[tree.tree_.feature[current_node]]
        word_count = int(input(f"{word}: "))

        next_node_array = (
            tree.tree_.children_right
            if word_count > 0
            else tree.tree_.children_left
        )

        next_node = next_node_array[current_node]

        if next_node == -1:
            break

        current_node = next_node

    return tree.classes_[np.argmax(tree.tree_.value[current_node][0])]


def play(redacted_title):
    redacted_title = str(redacted_title)  # Fire parses args smh

    with open('index.json') as f:
        index = json.load(f)

    articles = get_compatible_articles(index, redacted_title)
    tree, feature_names = build_decision_tree(index, articles)
    result = navigate_decision_tree(tree, feature_names)
    print(">>>", result)


if __name__ == '__main__':
    fire.Fire()
