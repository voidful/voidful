from phraseg import *
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import matplotlib as mpl
import arxivapi

mpl.rcParams['figure.dpi'] = 300

articles = arxivapi.query(search_query=['cs.CL'],
                          start_index=0, max_index=500, results_per_iteration=500,
                          wait_time=3.0, sort_by='lastUpdatedDate')

datas = ""
for a in articles:
    datas += a['title'] + "\n"
    datas += a['abstract'] + "\n"
print("Finish fetching")

phraseg = Phraseg(datas, idf_chunk=300)
result = phraseg.extract(result_word_minlen=1, merge_overlap=True)

wordcloud = WordCloud(font_path='wordcloud/NotoSansCJKtc-Medium.otf', width=1800, height=1000, margin=1,
                      background_color="white").fit_words(result)
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis("off")
plt.savefig('./wordcloud/wordcloud.png', bbox_inches='tight', pad_inches=0)
