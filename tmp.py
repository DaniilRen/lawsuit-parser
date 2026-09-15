import asyncio, json
from src.parsers.nalog_parser import NalogParser

async def diag():
    parser = NalogParser('nalog', {})
    await parser._setup_browser()
    await parser.page.goto(
        'https://pb.nalog.ru/company.html?token=699BE5A8220878247A673E89D399EF54797329680D6EDEF342E3DF96D3B3A746D917A566C758523FF5539FCF185EB156FA7D7C5DF885D3869A51415E7952D862',
        wait_until='domcontentloaded'
    )
    await parser.page.wait_for_timeout(5000)

    result = await parser.page.evaluate('''
        () => {
            const out = [];
            document.querySelectorAll('#pnlCompanyOtherInfo > .pb-company-multicolumn-item').forEach(item => {
                const id = item.getAttribute('id') || '';
                const header = item.querySelector('.pb-company-block-header');
                const fields = item.querySelectorAll('.pb-company-field');
                const blocks = item.querySelectorAll('.pb-company-block');
                const fullText = (item.textContent || '').trim();
                
                out.push({
                    id: id,
                    header: header ? header.textContent.trim() : null,
                    fieldCount: fields.length,
                    blockCount: blocks.length,
                    fullTextPreview: fullText.substring(0, 300),
                    htmlPreview: item.innerHTML.substring(0, 800)
                });
            });
            return out;
        }
    ''')

    print(json.dumps(result, indent=2, ensure_ascii=False))
    await parser._close()

asyncio.run(diag())
