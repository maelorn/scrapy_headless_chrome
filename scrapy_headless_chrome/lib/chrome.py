import asyncio
import logging
from pyppeteer import launch
from scrapy.http import HtmlResponse

logging.getLogger('websockets.protocol').setLevel(logging.WARNING)
logging.getLogger('pyppeteer').setLevel(logging.WARNING)


class ChromeRequest(object):
    def __init__(self, request):
        self.loop = asyncio.get_event_loop()
        self.request = request
        self.url = request.url
        self.loop.run_until_complete(self.launch_browser())

    async def launch_browser(self):
        # Not great should be a remote browser allready launched or a remote service
        self.browser = await launch(logLevel=None)
        self.page = await self.browser.newPage()
        await self.page.setExtraHTTPHeaders({str(k, "utf-8"): str(v[0], "utf-8") for k, v in self.request.headers.items() if k != "User-Agent"})
        await self.page.setUserAgent(str(self.request.headers["User-Agent"], "utf-8"))

    async def onInterceptedRequest(self, intercepted_request):
        data = {
            'method': self.request.method,
            'postData': self.request.body
        }
        intercepted_request.continue_(data)

    async def do_request(self):
        if self.request.method in ["POST", "PUT"]:
            await self.page.setRequestInterception(True)
            self.page.on('request', self.onInterceptedRequest)

        response = await self.page.goto(self.url)
        return response

    def get_response(self):
        response = self.loop.run_until_complete(self.do_request())
        page_content = self.loop.run_until_complete(self.page.content())
        print(response.headers)
        return HtmlResponse(
            url=self.url,
            status=response.status,
            headers={k: v for k, v in response.headers.items() if k != "content-encoding"},
            body=page_content,
            request=self.request,
            encoding='utf-8'
        )

    def stop(self):
        self.loop.run_until_complete(self.browser.close())