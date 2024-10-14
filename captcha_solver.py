import cv2
import numpy as np
import pytesseract

def solve_captcha(image_data):
    #print("--- [*] captcha service ---")
    image_array = np.frombuffer(image_data.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary_image_trimmed = binary_image[:, 2:-2]
    vertical_sum_trimmed = np.sum(binary_image_trimmed, axis=0)
    threshold = 520

    segments = []
    in_segment = False

    for i, value in enumerate(vertical_sum_trimmed):
        if not in_segment and value > threshold:
            start_idx = i + 2
            in_segment = True
        elif in_segment and value < threshold:
            end_idx = i + 2
            segments.append((start_idx, end_idx))
            in_segment = False

    cropped_segments = []

    for start, end in segments:
        segment = binary_image[:, start:end]
        segment = segment[1:-1, :]
        segment = cv2.copyMakeBorder(segment, 0, 0, 1, 1, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        horizontal_sum = np.sum(segment, axis=1)
        rows_with_content = np.where(horizontal_sum > 10)[0]
        top_row = rows_with_content[0]
        bottom_row = rows_with_content[-1]
        cropped_segment = segment[top_row:bottom_row+1, :]
        padded_segment = cv2.copyMakeBorder(cropped_segment, 1, 1, 0, 0, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        inverted_segment = cv2.bitwise_not(padded_segment)
        cropped_segments.append(inverted_segment)

    recognized_texts = []
    for segment in cropped_segments:
        text = pytesseract.image_to_string(segment, config='--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        recognized_texts.append(text.strip())

    return ''.join(recognized_texts)