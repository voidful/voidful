import urllib.request, json
from phraseg import *
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import matplotlib as mpl

mpl.rcParams['figure.dpi'] = 300


def read_url_data(open_url):
    try:
        with urllib.request.urlopen(open_url) as url:
            decoded_text = url.read().decode()
            return decoded_text
    except:
        return ""


daily_trending = json.loads(read_url_data("https://trendings.herokuapp.com/repo?lang=python&since=daily"))
trending = ""
for t in daily_trending['items'][:3]:
    url = t['repo_link'].replace('https://github.com/', 'https://raw.githubusercontent.com/')
    trending += read_url_data(url + "/main/README.md")
    trending += read_url_data(url + "/master/README.md")
print("Finish fetching repos")

phraseg = Phraseg(trending, idf_chunk=20000)
result = phraseg.extract(result_word_minlen=2)

wordcloud = WordCloud(font_path='wordcloud/NotoSansCJKtc-Medium.otf', width=1800, height=1000, margin=1,
                      background_color="white").fit_words(result)
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis("off")
plt.savefig('wordcloud/wordcloud.png', bbox_inches='tight', pad_inches=0)
