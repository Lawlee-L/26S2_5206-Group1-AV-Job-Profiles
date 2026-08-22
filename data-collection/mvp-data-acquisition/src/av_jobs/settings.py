"""Conservative Scrapy settings for public recruitment data collection."""

BOT_NAME = "av_jobs"

SPIDER_MODULES = ["av_jobs.spiders"]
NEWSPIDER_MODULE = "av_jobs.spiders"

USER_AGENT = (
    "CITS5206-UWA-AV-Job-Research/0.2 "
    "(+https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles)"
)

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 45
RETRY_TIMES = 2
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False
LOG_LEVEL = "INFO"

ITEM_PIPELINES = {
    "av_jobs.pipelines.ValidationExportPipeline": 300,
}

EXTENSIONS = {
    "av_jobs.extensions.source_status.SourceStatusExtension": 500,
}

FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
