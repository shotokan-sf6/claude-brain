import sys,asyncio
from playwright.async_api import async_playwright
async def main(p,shot):
  async with async_playwright() as pw:
    b=await pw.chromium.launch(); pg=await b.new_page(viewport={'width':1200,'height':900}); errs=[]
    pg.on('pageerror',lambda e: errs.append(str(e)))
    await pg.goto('file://'+p); await pg.wait_for_timeout(800)
    print('errors',errs); print('h1',await pg.inner_text('h1'))
    print('story chars',len(await pg.inner_text('[data-draw=story]')))
    await pg.screenshot(path=shot,full_page=True); await b.close()
asyncio.run(main(sys.argv[1],sys.argv[2]))
