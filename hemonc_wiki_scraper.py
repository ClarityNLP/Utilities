import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import unquote_plus

main_url = 'https://hemonc.org/'
edit_url = 'https://hemonc.org/w/index.php?title={}&action=edit'
ignored = ['/wiki/Editorial_Board', '/wiki/Category:Disease_index', '/wiki/Category:Intervention_index',
           '/wiki/Category:Regimen_index', '/wiki/Category:General_reference_pages']
keep_characters = ('-', ' ', '(', ')', '_')


class WikiScraper(scrapy.Spider):
    name = 'wikispider'
    start_urls = [main_url + 'wiki']

    def parse_text(self, response):
        meta = response.meta
        subject = meta['subject']
        textrea = response.css('textarea')
        if len(textrea) > 0:
            text = textrea[0].root.value

            with open('./cancer_wiki/{}.txt'.format(subject), 'w') as file:
                file.write(text)
        else:
            print('error with ', subject)

    def parse(self, response):
        for href in response.css('td>a::attr(href)'):
            print(href)
            href_txt = href.root
            if href_txt[0] != '#' and href_txt not in ignored:
                subject = "".join(c for c in unquote_plus(href_txt).replace('/wiki/', '') if c.isalnum() or c in keep_characters).rstrip()

                print('navigating to ', subject)
                yield response.follow(edit_url.format(href_txt.replace('/wiki/', '')), callback=self.parse_text, meta={'subject': subject})


if __name__ == "__main__":
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })

    process.crawl(WikiScraper)
    process.start()
