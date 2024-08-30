# auto-redactle

A proof of concept for a Redactle solver based on a 10 MB index of Wikipedia. Read more at http://blog.valentin.sh/redactle/

<video src="https://github.com/user-attachments/assets/aceefc3e-2fb3-490e-93cc-9cd7918a8b6b" width="352" height="720"></video>

## Installation

Clone this repository and install the requirements of `requirements.txt` in a virtual env.

## Usage

**Solve a Redactle**

```
python auto_redactle.py play '<redacted title>'
```

This builds a decision tree based on words memberships stored in `index.json` and ask for you to try words in Redactle.

**Rebuild the index**

The index is based on the [10,000 "articles every Wikipedia should have"](https://meta.wikimedia.org/wiki/List_of_articles_every_Wikipedia_should_have/Expanded). The set of articles as of September 2024 is stored in `urls.csv`, which you can use to save the articles locally (expected total size around 445 MB):

```
mkdir articles
python auto_redactle.py save_articles --folder articles
```

The command is idempotent (and doesn't download already downloaded articles), so you can re-run it as much as you want. But if you want to download the latest version of an article, you need to first remove it from the target folder.

You can then build the index from the local texts of the articles (shouldn't take more than a minute):

```
python auto_redactle.py build_index --folder articles
```

**Re-fetch the set of URLs**

If you want to update the set of the 10,000 URLs in `urls.py`:

```
python auto_redactle.py fetch_urls --urls_fn urls.csv
```

---

This is all very experimental and untested. Don't hesitate to open a PR to improve stuff.
