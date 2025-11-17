import os
from app_modules.common_tools import takePort

from gluon import current
from gluon.contrib.appconfig import AppConfig # type: ignore

request = current.request

def main():
    robot_txt = get_robots_txt()
    with open(os.path.join(request.folder,'static', 'robots.txt'), "w") as file:
        file.write(robot_txt)


def get_robots_txt():
    myconf = AppConfig(reload=True)

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: takePort(v)) # type: ignore

    sitemap = f"{scheme}://{host}"
    if port:
        sitemap = f"{sitemap}:{port}"
    if not sitemap.endswith('/'):
        sitemap += '/'
    sitemap = f"{sitemap}sitemap"
    print(sitemap)

    return """
# Disallow IA bots.

User-agent: GPTBot
User-agent: ChatGPT-User
User-agent: OAI-SearchBot
User-agent: Google-Extended
User-agent: ClaudeBot
User-agent: Claude-Web
User-agent: Claude-User
User-agent: Claude-SearchBot
User-agent: MetaBot
User-agent: ai-facebook
User-agent: PerplexityBot
User-agent: CCBot
User-agent: Amazonbot
User-agent: Applebot-Extended
User-agent: GoogleOther
User-agent: Omgilibot
User-agent: Omgili
User-agent: Applebot
User-agent: anthropic-ai
User-agent: Bytespider
User-agent: Diffbot
User-agent: ImagesiftBot
User-agent: YouBot
User-agent: cohere-ai
User-agent: DeepSeekBot
User-agent: DuckAssistBot
User-agent: Gemini-User
User-agent: Grok
User-agent: Meta-ExternalAgent
User-agent: MistralAI-User
User-agent: Perplexity-User
User-agent: Meta-ExternalFetcher
User-agent: cohere-training-data-crawler
User-agent: Webzio
User-agent: Webzio-Extended
User-agent: Gemini-Deep-Research
User-agent: Google-CloudVertexBot
User-agent: AI2Bot
User-agent: Kangaroo Bot
User-agent: PanguBot
User-agent: PetalBot
User-agent: SemrushBot-OCOB
User-agent: FacebookBot

Disallow: /

# Allow search engine bots.

User-agent: Googlebot
User-agent: Bingbot
User-agent: DuckDuckBot
User-agent: Slurp
User-agent: Baiduspider
User-agent: Yandexbot
User-agent: Qwantify

Allow: /

# Crawl delay for other bots.

User-agent: *
Crawl-delay: 4
Allow: /

Sitemap: {{sitemap}}

""".replace("{{sitemap}}", sitemap)

if __name__ == '__main__':
    main()
