import asyncio, json
from playwright.async_api import async_playwright

async def diag():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        await page.goto(
            'https://fedresurs.ru/companies/dd46185f-2798-498a-abab-b4924981f69e',
            wait_until='domcontentloaded'
        )
        await page.wait_for_timeout(8000)

        html = await page.evaluate("""
            (() => {
                const items = Array.from(document.querySelectorAll('information-page-item'));
                const eio = items.find(el =>
                    (el.getAttribute('header') || '').toLowerCase().includes('исполнительный')
                );
                if (!eio) return { found: false, headers: items.map(i => i.getAttribute('header')) };
                return {
                    found: true,
                    outerHTML: eio.outerHTML.substring(0, 5000),
                    textContent: eio.textContent.trim().substring(0, 1000),
                    childClasses: Array.from(eio.querySelectorAll('[class]')).slice(0, 40).map(el => ({
                        tag: el.tagName,
                        className: el.className,
                        text: el.textContent.trim().substring(0, 80)
                    }))
                };
            })()
        """)

        print(json.dumps(html, indent=2, ensure_ascii=False))
        await browser.close()

asyncio.run(diag())
