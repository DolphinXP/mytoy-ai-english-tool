## To enable OCR support for PyMuPDF, do this on Windows:

1. Install Tesseract
* Recommended: winget install UB-Mannheim.TesseractOCR
* Or download installer from UB Mannheim (Windows build): https://github.com/UB-Mannheim/tesseract/wiki
2. Add Tesseract to PATH
* Typical install path: C:\Program Files\Tesseract-OCR
* Add that folder to system/user PATH.
3. Ensure language data exists
* Check folder: C:\Program Files\Tesseract-OCR\tessdata
* Keep at least:
    * eng.traineddata
    * chi_sim.traineddata (if you read Chinese scanned PDFs)
4. (Optional) Set TESSDATA_PREFIX
* If OCR can’t find language files, set:
* TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
5. Verify in terminal
```
tesseract --version
tesseract --list-langs
```
You should see installed languages (like eng, chi_sim).