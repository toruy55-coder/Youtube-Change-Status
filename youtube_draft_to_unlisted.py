import asyncio
import os
import re
from playwright.async_api import async_playwright

YOUTUBE_STUDIO_URL = "https://studio.youtube.com"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

async def main():
    async with async_playwright() as p:
        print("Chromeを起動中...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = await context.new_page()
        await page.goto(YOUTUBE_STUDIO_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        current_url = page.url
        channel_id_match = re.search(r"/channel/([^/]+)", current_url)
        if not channel_id_match:
            print(f"チャンネルIDが取得できませんでした。URL: {current_url}")
            await context.close()
            return

        channel_id = channel_id_match.group(1)
        print(f"チャンネルID: {channel_id}")

        await page.goto(f"{YOUTUBE_STUDIO_URL}/channel/{channel_id}/videos")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        processed = 0

        while True:
            rows = await page.query_selector_all("ytcp-video-row")
            print(f"動画行数: {len(rows)}")

            draft_found = False
            for row in rows:
                row_text = await row.inner_text()
                if "ドラフト" not in row_text:
                    continue

                # 「ドラフトを編集」ボタンを探す
                edit_btn = await row.query_selector("text=ドラフトを編集")
                if not edit_btn:
                    # リンク要素を直接探す
                    edit_btn = await row.query_selector("a[href*='video_id']")
                if not edit_btn:
                    print("  編集ボタンが見つかりません。スキップします。")
                    continue

                title_lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                title = title_lines[1] if len(title_lines) > 1 else "不明"
                print(f"  ドラフト検出: {title}")

                await edit_btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)

                # 「公開設定」タブへ移動（ステップ4番目）
                visibility_tab = await page.query_selector(
                    "button#step-badge-3, [data-tab-id='3'], button[aria-label*='公開'], button[aria-label*='visibility']"
                )
                if visibility_tab:
                    await visibility_tab.click()
                    await asyncio.sleep(1)
                else:
                    # タブが見つからない場合、直接「限定公開」ラジオを探す
                    print("  公開設定タブが見つかりません。直接ラジオボタンを探します。")

                # 「限定公開」ラジオボタンを選択
                unlisted = await page.query_selector(
                    "tp-yt-paper-radio-button[name='UNLISTED'], [name='UNLISTED']"
                )
                if unlisted:
                    await unlisted.click()
                    await asyncio.sleep(1)
                    print("  限定公開を選択しました")
                else:
                    print("  限定公開ボタンが見つかりません")

                # 保存ボタン
                save_btn = await page.query_selector(
                    "ytcp-button#save-button, button[aria-label*='保存'], ytcp-button:has-text('保存')"
                )
                if save_btn:
                    await save_btn.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    processed += 1
                    print(f"✅ {processed}本目を限定公開に変更しました: {title}")
                else:
                    print("  保存ボタンが見つかりません")

                # コンテンツ一覧に戻る
                await page.goto(f"{YOUTUBE_STUDIO_URL}/channel/{channel_id}/videos")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                draft_found = True
                break

            if not draft_found:
                print(f"\n🎉 完了！合計 {processed} 本を限定公開に変更しました。")
                break

        await asyncio.sleep(3)
        await context.close()

asyncio.run(main())
