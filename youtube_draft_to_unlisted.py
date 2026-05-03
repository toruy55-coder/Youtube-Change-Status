import argparse
import asyncio
import os
import re
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

YOUTUBE_STUDIO_URL = "https://studio.youtube.com"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

PRIVATE_SHARE_EMAILS = [
    "toruy56@gmail.com",
    "mei1218y@gmail.com",
    "m.reveson.mi@gmail.com",
    "rihoho1020@gmail.com",
    "memory.yoshie55@gmail.com",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="YouTube Studio のドラフト動画を非公開にし、指定Googleアカウントだけに共有します。"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="処理する本数の上限。例: --limit 1",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="1本だけ処理するテストモード。--limit 1 と同じです。",
    )
    parser.add_argument(
        "--skip-confirm",
        action="store_true",
        help="起動後のEnter待ちをスキップします。",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="ドラフトに加えて、既に非公開になった動画も共有先設定の対象にします。",
    )
    return parser.parse_args()


async def first_visible(page_or_locator, selectors, timeout=2500):
    for selector in selectors:
        locator = page_or_locator.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            continue
    return None


async def click_first_visible(page_or_locator, selectors, timeout=2500):
    locator = await first_visible(page_or_locator, selectors, timeout=timeout)
    if not locator:
        return False
    await robust_click(locator)
    return True


async def robust_click(locator):
    try:
        await locator.click(timeout=7000)
        return
    except PlaywrightTimeoutError:
        pass

    try:
        await locator.click(force=True, timeout=7000)
        return
    except PlaywrightTimeoutError:
        pass

    await locator.evaluate(
        """(element) => {
            const clickable = element.querySelector(
                'button, tp-yt-paper-button, paper-button, #button'
            ) || element;
            clickable.click();
        }"""
    )


async def click_by_locator_box(page, locator):
    box = await locator.bounding_box()
    if not box:
        return False
    await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    return True


async def click_dialog_invite_area(page, dialog):
    box = await dialog.bounding_box()
    if not box:
        return False
    await page.mouse.click(box["x"] + 48, box["y"] + 185)
    return True


async def click_dialog_done_button(page, dialog):
    box = await dialog.bounding_box()
    if not box:
        return False
    await page.mouse.click(box["x"] + box["width"] - 62, box["y"] + box["height"] - 38)
    return True


async def wait_hidden(locator, timeout=2500):
    try:
        await locator.wait_for(state="hidden", timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


async def press_tab_enter(page, tab_count=1):
    for _ in range(tab_count):
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.2)
    await page.keyboard.press("Enter")


async def focused_text(page):
    return await page.evaluate(
        """() => {
            const element = document.activeElement;
            if (!element) return '';
            return [
                element.innerText,
                element.textContent,
                element.getAttribute('aria-label'),
                element.getAttribute('id'),
            ].filter(Boolean).join(' ');
        }"""
    )


async def press_tabs_then_key_if_done(page, tab_count, key):
    for _ in range(tab_count):
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.2)

    text = await focused_text(page)
    print(f"    フォーカス中: {text[:80]}")
    if "キャンセル" in text:
        print("    キャンセルにフォーカスしているため押しません")
        return False
    if "完了" not in text and "保存" not in text and "done-button" not in text:
        print("    完了/保存ではないため押しません")
        return False

    await page.keyboard.press(key)
    return True


async def focus_locator_then_key(page, locator, key):
    await locator.evaluate("(element) => element.focus()")
    await asyncio.sleep(0.2)
    await page.keyboard.press(key)


async def dialog_contains_all_emails(dialog):
    text = await dialog.evaluate(
        """(element) => {
            const values = [...element.querySelectorAll('input, textarea')]
                .map((input) => input.value || '')
                .join(' ');
            return [element.innerText || '', element.textContent || '', values].join(' ');
        }"""
    )
    missing = [email for email in PRIVATE_SHARE_EMAILS if email not in text]
    if missing:
        print("  共有先メールが画面上で確認できません:")
        for email in missing:
            print(f"    - {email}")
        return False
    return True


async def goto_with_wait(page, url):
    await page.goto(url)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    await asyncio.sleep(2)


async def get_channel_id(page):
    current_url = page.url
    channel_id_match = re.search(r"/channel/([^/]+)", current_url)
    if channel_id_match:
        return channel_id_match.group(1)

    print(f"チャンネルIDがURLから取得できませんでした。現在のURL: {current_url}")
    print("YouTube Studio のダッシュボードが表示されている状態にしてからEnterを押してください...")
    input()
    channel_id_match = re.search(r"/channel/([^/]+)", page.url)
    return channel_id_match.group(1) if channel_id_match else None


async def find_target_row(page, include_private=False):
    rows = await page.query_selector_all("ytcp-video-row")
    print(f"動画行数: {len(rows)}")

    for row in rows:
        row_text = await row.inner_text()
        is_draft = "ドラフト" in row_text
        is_private = include_private and "非公開" in row_text
        if is_draft or is_private:
            title_lines = [line.strip() for line in row_text.split("\n") if line.strip()]
            title = title_lines[1] if len(title_lines) > 1 else "不明"
            status = "ドラフト" if is_draft else "非公開"
            return row, title, status

    return None, None, None


async def open_video_editor(row):
    edit_btn = await row.query_selector("text=ドラフトを編集")
    if not edit_btn:
        edit_btn = await row.query_selector("a[href*='video_id']")
    if not edit_btn:
        edit_btn = await row.query_selector("a[href*='/video/']")
    if not edit_btn:
        edit_btn = await row.query_selector("a")
    if not edit_btn:
        return False
    await edit_btn.click()
    return True


async def open_visibility_step(page):
    clicked = await click_first_visible(
        page,
        [
            "button#step-badge-3",
            "[data-tab-id='3']",
            "button[aria-label*='公開']",
            "button[aria-label*='visibility']",
            "text=公開設定",
        ],
    )
    await asyncio.sleep(1)
    return clicked


async def choose_private(page):
    private_radio = await first_visible(
        page,
        [
            "tp-yt-paper-radio-button[name='PRIVATE']",
            "[name='PRIVATE']",
            "tp-yt-paper-radio-button:has-text('非公開')",
            "div[role='radio']:has-text('非公開')",
            "text=非公開",
        ],
    )
    if not private_radio:
        return False

    await robust_click(private_radio)
    await asyncio.sleep(1)
    return True


async def open_private_share_dialog(page):
    opened = await click_first_visible(
        page,
        [
            "ytcp-button:has-text('動画を非公開で共有')",
            "ytcp-button:has-text('非公開で共有')",
            "button:has-text('動画を非公開で共有')",
            "button:has-text('非公開で共有')",
            "a:has-text('動画を非公開で共有')",
            "a:has-text('非公開で共有')",
            "text=動画を非公開で共有",
            "text=非公開で共有",
        ],
        timeout=3500,
    )
    if opened:
        await asyncio.sleep(1)
    return opened


async def add_private_share_emails(page):
    dialog = await first_visible(
        page,
        [
            "div[role='dialog']:has-text('動画を非公開で共有')",
            "tp-yt-paper-dialog:has-text('動画を非公開で共有')",
            "ytcp-dialog:has-text('動画を非公開で共有')",
            "paper-dialog:has-text('動画を非公開で共有')",
            "div[role='dialog']:has-text('招待するユーザー')",
            "tp-yt-paper-dialog:has-text('招待するユーザー')",
        ],
        timeout=5000,
    )
    if not dialog:
        print("  非公開共有ダイアログ本体が見つかりません")
        return False

    input_selectors = [
        "input[type='email']",
        "input[aria-label*='招待']",
        "input[aria-label*='メール']",
        "input[aria-label*='email']",
        "textarea[aria-label*='招待']",
        "textarea[aria-label*='メール']",
        "textarea[aria-label*='email']",
        "[contenteditable='true']",
        "textarea",
        "input",
    ]

    email_input = await first_visible(dialog, input_selectors, timeout=2500)
    if not email_input:
        if not await click_dialog_invite_area(page, dialog):
            print("  共有メール入力欄が見つかりません")
            return False
        print("  入力欄を直接特定できないため、招待欄の中央付近をクリックして入力します")

    for email in PRIVATE_SHARE_EMAILS:
        if email_input:
            await robust_click(email_input)
            try:
                await email_input.fill(email)
            except PlaywrightTimeoutError:
                await page.keyboard.press("Meta+A")
                await page.keyboard.type(email)
        else:
            await page.keyboard.type(email)
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.7)
        print(f"  共有先を追加: {email}")

    await asyncio.sleep(1)
    if not await dialog_contains_all_emails(dialog):
        return False

    done_button = await first_visible(
        dialog,
        [
            "ytcp-button#done-button",
            "ytcp-button:has-text('完了')",
            "ytcp-button:has-text('保存')",
            "button:has-text('完了')",
            "button:has-text('保存')",
            "text=完了",
            "text=保存",
        ],
        timeout=3000,
    )
    if not done_button:
        print("  非公開共有ダイアログの完了ボタンが見つかりません")
        return False

    close_attempts = [
        ("右下の完了ボタンを座標クリック", lambda: click_dialog_done_button(page, dialog)),
        ("完了ボタン中央を座標クリック", lambda: click_by_locator_box(page, done_button)),
        ("完了ボタンを強制クリック", lambda: robust_click(done_button)),
    ]
    for label, action in close_attempts:
        print(f"  非公開共有ダイアログを閉じる試行: {label}")
        try:
            await action()
        except PlaywrightTimeoutError:
            pass
        await asyncio.sleep(1)
        if await wait_hidden(dialog, timeout=2500):
            await asyncio.sleep(1)
            print("  非公開共有ダイアログを閉じました")
            return True

    print("  非公開共有ダイアログを閉じたことを確認できません")
    return False


async def save_changes(page):
    save_btn = await first_visible(
        page,
        [
            "ytcp-button#save-button",
            "ytcp-uploads-dialog ytcp-button#done-button:has-text('保存')",
            "ytcp-button:has-text('保存')",
            "button[aria-label*='保存']",
            "button:has-text('保存')",
        ],
        timeout=4000,
    )
    if not save_btn:
        print("  最終保存ボタンが見つかりません")
        return False

    await robust_click(save_btn)
    print("  最終保存ボタンをクリックしました")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    saved_signal = await first_visible(
        page,
        [
            "text=保存しました",
            "text=変更を保存しました",
            "text=動画を保存しました",
            "text=保存済み",
        ],
        timeout=8000,
    )
    if saved_signal:
        return True

    try:
        await save_btn.wait_for(state="hidden", timeout=5000)
        return True
    except PlaywrightTimeoutError:
        pass

    disabled = await save_btn.get_attribute("aria-disabled")
    if disabled == "true":
        return True

    return False


async def confirm_saved_on_list(page, channel_id, title):
    await goto_with_wait(page, f"{YOUTUBE_STUDIO_URL}/channel/{channel_id}/videos")
    rows = await page.query_selector_all("ytcp-video-row")
    for row in rows:
        row_text = await row.inner_text()
        if title in row_text:
            if "非公開" in row_text and "ドラフト" not in row_text:
                return True
            print("  一覧で保存後ステータスを確認できませんでした。")
            print(f"  該当行: {row_text.replace(chr(10), ' | ')}")
            return False
    print("  一覧で対象動画の行が見つかりませんでした。")
    return False


async def process_one_video(page, channel_id, include_private=False):
    row, title, status = await find_target_row(page, include_private=include_private)
    if not row:
        return False, None, "no_target"

    print(f"  対象検出（{status}）: {title}")
    if not await open_video_editor(row):
        return False, title, "edit_button_not_found"

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    await asyncio.sleep(3)

    if not await open_visibility_step(page):
        print("  公開設定タブが見つかりません。現在画面で非公開設定を直接探します。")

    if not await choose_private(page):
        return False, title, "private_radio_not_found"
    print("  非公開を選択しました")

    if not await open_private_share_dialog(page):
        return False, title, "private_share_dialog_not_found"
    print("  非公開共有ダイアログを開きました")

    if not await add_private_share_emails(page):
        return False, title, "share_email_input_not_found"

    save_confirmed = await save_changes(page)
    list_confirmed = await confirm_saved_on_list(page, channel_id, title)
    if not save_confirmed:
        print("  保存完了メッセージは確認できませんでした。")
    if not list_confirmed:
        return False, title, "save_not_confirmed"

    return True, title, "saved"


async def main():
    args = parse_args()
    limit = 1 if args.test else args.limit

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
        await goto_with_wait(page, YOUTUBE_STUDIO_URL)

        print("共有先Googleアカウント:")
        for email in PRIVATE_SHARE_EMAILS:
            print(f"  - {email}")
        print("YouTube Studio が表示され、正しいアカウントであることを確認したらEnterを押してください...")
        if not args.skip_confirm:
            input()

        channel_id = await get_channel_id(page)
        if not channel_id:
            print(f"チャンネルIDが取得できませんでした。URL: {page.url}")
            await context.close()
            return

        print(f"チャンネルID: {channel_id}")
        await goto_with_wait(page, f"{YOUTUBE_STUDIO_URL}/channel/{channel_id}/videos")

        processed = 0
        failures = []

        while True:
            if limit is not None and processed >= limit:
                print(f"\nテスト/上限モードのため {processed} 本で停止しました。")
                break

            success, title, reason = await process_one_video(
                page,
                channel_id,
                include_private=args.include_private,
            )
            if reason == "no_target":
                break

            if success:
                processed += 1
                print(f"✅ {processed}本目を非公開＋指定5アカウント共有に変更しました: {title}")
                continue

            failures.append((title or "不明", reason))
            print(f"❌ 処理失敗: {title or '不明'} / 理由: {reason}")
            break

        print(f"\n完了。成功: {processed} 本 / 失敗: {len(failures)} 本")
        if failures:
            for title, reason in failures:
                print(f"  - {title}: {reason}")

        await asyncio.sleep(3)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
