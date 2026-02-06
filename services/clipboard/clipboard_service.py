"""
Clipboard service for capturing text from Windows clipboard.
"""
import win32clipboard
import win32con


class ClipboardService:
    """Service for accessing Windows clipboard."""

    def __init__(self):
        pass

    def get_text(self):
        """
        Get text from clipboard with comprehensive format support.

        Returns:
            Tuple of (text, format_name)
        """
        try:
            win32clipboard.OpenClipboard()

            # Try different clipboard formats
            formats_to_try = [
                (win32con.CF_UNICODETEXT, "Unicode Text"),
                (win32con.CF_TEXT, "ANSI Text"),
                (win32con.CF_OEMTEXT, "OEM Text")
            ]

            available_formats = []
            format_id = 0
            while True:
                format_id = win32clipboard.EnumClipboardFormats(format_id)
                if format_id == 0:
                    break
                available_formats.append(format_id)

            print(f"Available clipboard formats: {available_formats}")

            for format_id, format_name in formats_to_try:
                if format_id in available_formats:
                    try:
                        data = win32clipboard.GetClipboardData(format_id)
                        win32clipboard.CloseClipboard()
                        print(
                            f"Successfully read {format_name}: {len(data) if data else 0} characters")
                        return data, format_name
                    except Exception as e:
                        print(f"Failed to read {format_name}: {e}")
                        continue

            win32clipboard.CloseClipboard()
            print("No readable text format found in clipboard")
            return "", "No Format"

        except Exception as e:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            print(f"Clipboard access error: {e}")
            return "", "Error"
