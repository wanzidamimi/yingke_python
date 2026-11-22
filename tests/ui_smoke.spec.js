const { test, expect } = require('playwright/test');

test('danmaku stream stays inside a bounded console panel', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://127.0.0.1:8801');
  await page.waitForLoadState('networkidle');

  const list = page.locator('#list');
  await expect(list).toBeVisible();

  await page.evaluate(() => {
    for (let i = 0; i < 120; i += 1) {
      append({
        kind: 'danmu',
        category: 'danmu',
        user: `测试用户${i + 1}`,
        text: `这是一条用于验证布局边界的弹幕内容，编号 ${i + 1}`,
      });
    }
  });
  await page.waitForTimeout(100);

  const box = await list.boundingBox();
  expect(box).toBeTruthy();
  expect(box.height).toBeLessThan(720); // 900px viewport x 0.8
  await expect.poll(() => page.evaluate(() => ({
    overflow: document.scrollingElement.scrollWidth - window.innerWidth,
    classPresent: Boolean(document.querySelector('.workspace')),
  }))).toMatchObject({ overflow: expect.any(Number), classPresent: true });
  await expect.poll(async () => (await page.evaluate(() => document.scrollingElement.scrollWidth - window.innerWidth))).toBeLessThanOrEqual(1);
});

