CRACKER WINGO SCANNER — WINDOWS EXE BUILDER

This package is the Windows source + one-click EXE builder. It is not itself a precompiled EXE.
The actual .exe is created on your Windows laptop by BUILD_EXE.bat.

INSTALL / BUILD
1. Download and extract this ZIP on your Windows laptop.
2. Install Python 3.11+ from https://www.python.org/downloads/windows/
   IMPORTANT: tick "Add Python to PATH".
3. Install Tesseract OCR for Windows from:
   https://github.com/UB-Mannheim/tesseract/wiki
   Default path: C:\Program Files\Tesseract-OCR\tesseract.exe
4. Double-click BUILD_EXE.bat and wait.
5. Final executable: dist\CrackerWingoScanner.exe

HOW TO USE
1. Open B9.Game -> Win Go -> Game History.
2. Launch CrackerWingoScanner.exe.
3. Select HISTORY area and drag around the rows containing Period ID and Number.
4. Click Capture history now. The app derives Big/Small and common Win Go colour mapping.
5. If no new periods are detected, scroll the site's history table to older rows and click "I opened next page — scan again". The app prompts you when it sees no new rows.
6. For Chart/Statistics, open the site's Chart page. Select CHART area around Winning Number / Missing / Avg Missing / Frequency / Max Consecutive and click Capture chart / statistics.
7. If chart page is not open, the app tells you to open it. It does not navigate or click the website automatically.
8. Data is saved under Documents\CrackerWingoScanner\

WHAT IT CURRENTLY READS
- History table OCR: period ID and one-digit winning number; derives Big/Small and colour.
- Chart statistics: OCR text capture saved to chart_ocr_log.txt and shown in app.
- Repeated adjacent transitions and repeated 3-digit sequences are counted from collected history.

IMPORTANT LIMITS
- The app only reads pixels visible in the selected screen region. It cannot inspect hidden tabs, hidden pages, or a browser's private internal data.
- If text is blurred, angled, tiny, or cut off, OCR can misread it. Verify rows before analysis.
- Chart OCR currently captures and displays the visible statistics text; it does not yet robustly map every chart statistic into structured columns. That requires calibration against a clear direct screenshot or screen capture from your actual display.
- It does not place bets or claim guaranteed next-result predictions. Repeated sequences are descriptive, not proof of an edge.
- MACD is a price-series indicator and is not a valid predictive signal for independent lottery digits.
