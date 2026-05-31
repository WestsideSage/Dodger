import os

tests = [
    'tests/e2e/official-rules-replay.spec.ts',
    'tests/e2e/replay-score-parity.spec.ts',
    'tests/e2e/tier1_recognition.spec.ts',
    'tests/e2e/v13_broadcast_layer.spec.ts'
]

dismiss_code = """
  const previewContinue = page.getByRole('button', { name: /continue to the command desk/i });
  if (await previewContinue.isVisible({ timeout: 2000 })) {
    await previewContinue.click();
    await page.waitForTimeout(500);
  }"""

for test_path in tests:
    with open(test_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    target = "await expect(page.getByTestId('weekly-command-center')).toBeVisible();"
    if target in content and "previewContinue" not in content:
        content = content.replace(target, dismiss_code + "\n  " + target)
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {test_path}")
